import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..models.state_machine import ExamState
from ..services.exam_service import ExamService

router = APIRouter(prefix="/api/exam", tags=["exam"])


# 请求/响应模型
class TopicRequest(BaseModel):
    topic: str


class AnswerRequest(BaseModel):
    answer: str


class ExamResponse(BaseModel):
    state: str
    message: str
    data: Optional[Dict] = None


# 存储考试会话
exam_sessions: Dict[str, ExamService] = {}


# RESTful API 端点
@router.post("/start")
async def start_exam(topic_request: TopicRequest) -> ExamResponse:
    """启动新的考试会话"""
    exam_service = ExamService()
    session_id = str(uuid.uuid4())
    exam_sessions[session_id] = exam_service

    try:
        # 处理主题选择
        result = await exam_service.process_answer(topic_request.topic)

        # 如果成功选择主题，自动开始考试
        if result.get("type") == "state_change" and result.get("state") == "TOPIC_SELECTED":
            await exam_service.start_exam(topic_request.topic)

        return ExamResponse(
            state=exam_service.state_machine.get_current_state().value,
            message="考试会话已创建并开始",
            data={
                "session_id": session_id,
                "result": result,
                "current_question": exam_service.state_machine.get_current_question(),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/answer")
async def submit_answer(session_id: str, answer_request: AnswerRequest) -> ExamResponse:
    """提交答案"""
    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        raise HTTPException(status_code=404, detail="考试会话不存在")

    try:
        result = await exam_service.process_answer(answer_request.answer)
        return ExamResponse(
            state=exam_service.state_machine.get_current_state().value,
            message="回答已处理",
            data={
                "result": result,
                "current_question": exam_service.state_machine.get_current_question(),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/state")
async def get_exam_state(session_id: str) -> ExamResponse:
    """获取考试状态"""
    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        raise HTTPException(status_code=404, detail="考试会话不存在")

    return ExamResponse(
        state=exam_service.state_machine.get_current_state().value,
        message="当前考试状态",
        data={
            "context": exam_service.state_machine.context,
            "current_question": exam_service.state_machine.get_current_question(),
        },
    )


@router.get("/{session_id}/evaluation")
async def get_evaluation(session_id: str) -> ExamResponse:
    """获取考试评估结果"""
    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        raise HTTPException(status_code=404, detail="考试会话不存在")

    if exam_service.state_machine.get_current_state() != ExamState.COMPLETED:
        raise HTTPException(status_code=400, detail="考试尚未完成")

    evaluation = exam_service._generate_final_evaluation()
    return ExamResponse(state=ExamState.COMPLETED.value, message="考试评估结果", data=evaluation)


# WebSocket 端点
@router.websocket("/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 连接处理实时交互"""
    await websocket.accept()

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        await websocket.close(code=4000, reason="考试会话不存在")
        return

    try:
        while True:
            try:
                # 接收消息
                data = await websocket.receive_json()

                # 处理消息
                if "answer" in data:
                    result = await exam_service.process_answer(data["answer"])

                    # 发送响应
                    await websocket.send_json(
                        {
                            "type": "response",
                            "state": exam_service.state_machine.get_current_state().value,
                            "data": {
                                "result": result,
                                "current_question": exam_service.state_machine.get_current_question(),
                            },
                        }
                    )
            except WebSocketDisconnect:
                print(f"WebSocket connection closed for session {session_id}")
                break
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        try:
            await websocket.close()
        except:
            pass
