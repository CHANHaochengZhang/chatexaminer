import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..models.state_machine import ExamState
from ..services.exam_service import ExamService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("exam_api.log")],
)
logger = logging.getLogger(__name__)

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
    session_id = str(uuid.uuid4())
    logger.info(f"New exam session started - SessionID: {session_id}, Topic: {topic_request.topic}")

    exam_service = ExamService()
    exam_sessions[session_id] = exam_service

    try:
        # 处理主题选择
        result = await exam_service.process_answer(topic_request.topic)

        # 如果成功选择主题，自动开始考试
        if result.get("type") == "state_change" and result.get("state") == "TOPIC_SELECTED":
            await exam_service.start_exam(topic_request.topic)
            logger.info(f"Exam successfully initiated - SessionID: {session_id}")

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
        logger.error(f"Failed to start exam - SessionID: {session_id}, Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/answer")
async def submit_answer(session_id: str, answer_request: AnswerRequest) -> ExamResponse:
    """提交答案"""
    logger.info(f"Answer submission received - SessionID: {session_id}")

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Process answer and let GPT function calling handle state transitions
        result = await exam_service.process_answer(answer_request.answer)
        progress_data = exam_service.get_progress_evaluation()

        current_state = exam_service.state_machine.get_current_state().value
        logger.info(
            f"Answer processing completed - SessionID: {session_id}, State: {current_state}"
        )

        # Handle different response types
        if result.get("type") == "chat":
            return ExamResponse(
                state=current_state,
                message=result["content"],  # Use the chat response as message
                data={"type": "chat", "content": result["content"], "progress": progress_data},
            )
        elif result.get("type") == "question":
            return ExamResponse(
                state=current_state,
                message=result["content"],  # Use the question content as message
                data={
                    "result": result,
                    "current_question": exam_service.state_machine.get_current_question(),
                    "progress": progress_data,
                },
            )
        elif result.get("type") == "complete":
            return ExamResponse(
                state=current_state,
                message=result["content"],  # Use completion message
                data={
                    "result": result,
                    "evaluation": result.get("evaluation"),
                    "progress": progress_data,
                },
            )
        else:
            # Default case
            return ExamResponse(
                state=current_state,
                message=result.get("content", "Processing completed"),
                data={
                    "result": result,
                    "current_question": exam_service.state_machine.get_current_question(),
                    "progress": progress_data,
                },
            )
    except Exception as e:
        logger.error(f"Failed to process answer - SessionID: {session_id}, Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/progress")
async def get_progress_evaluation(session_id: str) -> ExamResponse:
    """获取考试进度评估"""
    logger.info(f"Progress evaluation requested - SessionID: {session_id}")

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="考试会话不存在")

    progress_data = exam_service.get_progress_evaluation()
    logger.info(
        f"Progress evaluation completed - SessionID: {session_id}, Questions Answered: {progress_data['stats']['questions_answered']}"
    )

    return ExamResponse(
        state=exam_service.state_machine.get_current_state().value,
        message="当前进度评估",
        data=progress_data,
    )


@router.get("/{session_id}/state")
async def get_exam_state(session_id: str) -> ExamResponse:
    """获取考试状态"""
    logger.info(f"Exam state requested - SessionID: {session_id}")

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="考试会话不存在")

    current_state = exam_service.state_machine.get_current_state().value
    logger.info(f"Exam state returned - SessionID: {session_id}, State: {current_state}")

    return ExamResponse(
        state=current_state,
        message="当前考试状态",
        data={
            "context": exam_service.state_machine.context,
            "current_question": exam_service.state_machine.get_current_question(),
        },
    )


@router.get("/{session_id}/evaluation")
async def get_evaluation(session_id: str) -> ExamResponse:
    """获取考试评估结果"""
    logger.info(f"Evaluation requested - SessionID: {session_id}")

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="考试会话不存在")

    current_state = exam_service.state_machine.get_current_state()
    if current_state != ExamState.COMPLETED:
        logger.info(
            f"Exam not completed, returning progress - SessionID: {session_id}, State: {current_state}"
        )
        progress_data = exam_service.get_progress_evaluation()
        return ExamResponse(
            state=current_state.value, message="考试尚未完成，返回当前进度评估", data=progress_data
        )

    evaluation = exam_service._generate_final_evaluation()
    logger.info(
        f"Final evaluation generated - SessionID: {session_id}, Total Score: {evaluation.get('total_score', 0)}"
    )

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
