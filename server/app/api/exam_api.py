import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..models.state_machine import ExamState
from ..services.exam_service import ExamService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("exam_api.log")],
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exam", tags=["exam"])


# Request/Response models
class TopicRequest(BaseModel):
    topic: str


class AnswerRequest(BaseModel):
    answer: str


class ExamResponse(BaseModel):
    state: str
    message: str
    data: Optional[Dict] = None


# Store exam sessions
exam_sessions: Dict[str, ExamService] = {}


# RESTful API endpoints
@router.post("/start")
async def start_exam(topic_request: TopicRequest) -> ExamResponse:
    """Start a new exam session"""
    session_id = str(uuid.uuid4())
    logger.info(f"New exam session started - SessionID: {session_id}, Topic: {topic_request.topic}")

    exam_service = ExamService()
    exam_sessions[session_id] = exam_service

    try:
        # Process topic selection
        result = await exam_service.process_answer(topic_request.topic)

        # If topic selection successful, automatically start exam
        if result.get("type") == "state_change" and result.get("state") == "TOPIC_SELECTED":
            await exam_service.start_exam(topic_request.topic)
            logger.info(f"Exam successfully initiated - SessionID: {session_id}")

        return ExamResponse(
            state=exam_service.state_machine.get_current_state().value,
            message="Exam session created and started",
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
    """Submit answer for current question"""
    logger.info(f"Answer submitted - SessionID: {session_id}")

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # 获取当前状态
        current_state = exam_service.state_machine.get_current_state()

        # 根据当前状态选择不同的处理方法
        if current_state == "CHAT":
            # 在CHAT状态下使用process_chat_answer方法
            logger.info(f"Processing chat answer - SessionID: {session_id}")
            try:
                result = await exam_service.process_chat_answer(answer_request.answer)
            except Exception as e:
                logger.error(
                    f"Error processing chat answer - SessionID: {session_id}, Error: {str(e)}"
                )
                # 如果处理失败，提供一个紧急回退响应
                result = {
                    "type": "chat",
                    "content": "抱歉，处理您的消息时出现了问题。您可以尝试继续考试或提出一个不同的问题。",
                }
                # 记录错误但继续处理
        else:
            # 其他状态使用原有的process_answer方法
            logger.info(f"Processing regular answer - SessionID: {session_id}")
            result = await exam_service.process_answer(answer_request.answer)

        # 获取处理后的状态（可能已经改变）
        current_state = exam_service.state_machine.get_current_state()
        logger.info(f"Answer processed - SessionID: {session_id}, State: {current_state}")

        # 根据当前状态提供更有意义的默认消息
        default_message = "Answer processed"
        if current_state == "QUESTIONING":
            default_message = "Okay, let's continue with the exam questions. Please think carefully before answering."
        elif current_state == "CHAT":
            default_message = "I understand you want to take a break. We can chat casually, just let me know when you're ready to continue the exam."
        elif current_state == "EXPLAINING":
            default_message = (
                "This concept seems to need a more detailed explanation, let me clarify it for you."
            )
        elif current_state == "EVALUATING":
            default_message = "The exam part has ended, I will evaluate your performance."
        elif current_state == "COMPLETED":
            default_message = "The exam is completed, you can view your evaluation report now."
        elif current_state == "INIT":
            default_message = "Please select a topic to start the exam."
        elif current_state == "TOPIC_SELECTED":
            default_message = "The topic has been selected, we are ready to start the exam."

        return ExamResponse(
            state=current_state,  # 直接使用状态字符串
            message=result.get("message", default_message),
            data=result,
        )
    except Exception as e:
        logger.error(f"Failed to process answer - SessionID: {session_id}, Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/progress")
async def get_progress_evaluation(session_id: str) -> ExamResponse:
    """Get exam progress evaluation"""
    logger.info(f"Progress evaluation requested - SessionID: {session_id}")

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    progress_data = exam_service.get_progress_evaluation()
    logger.info(
        f"Progress evaluation completed - SessionID: {session_id}, Questions Answered: {progress_data['stats']['questions_answered']}"
    )

    return ExamResponse(
        state=exam_service.state_machine.get_current_state(),  # 直接使用状态字符串
        message="Current progress evaluation",
        data=progress_data,
    )


@router.get("/{session_id}/state")
async def get_exam_state(session_id: str) -> ExamResponse:
    """Get exam state"""
    logger.info(f"Exam state requested - SessionID: {session_id}")

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    current_state = exam_service.state_machine.get_current_state()
    logger.info(f"Exam state returned - SessionID: {session_id}, State: {current_state}")

    return ExamResponse(
        state=current_state,
        message="Current exam state",
        data={
            "context": exam_service.state_machine.context,
            "current_question": exam_service.state_machine.get_current_question(),
        },
    )


@router.get("/{session_id}/evaluation")
async def get_evaluation(session_id: str) -> ExamResponse:
    """Get exam evaluation results"""
    logger.info(f"Evaluation requested - SessionID: {session_id}")

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    current_state = exam_service.state_machine.get_current_state()
    if current_state != ExamState.COMPLETED:
        logger.info(
            f"Exam not completed, returning progress - SessionID: {session_id}, State: {current_state}"
        )
        progress_data = exam_service.get_progress_evaluation()
        return ExamResponse(
            state=current_state.value,
            message="Exam not completed, returning current progress evaluation",
            data=progress_data,
        )

    evaluation = await exam_service._generate_final_evaluation()
    logger.info(
        f"Final evaluation generated - SessionID: {session_id}, Total Score: {evaluation.get('total_score', 0)}"
    )

    return ExamResponse(
        state=ExamState.COMPLETED.value, message="Exam evaluation results", data=evaluation
    )


@router.get("/{session_id}/hint")
async def request_hint(session_id: str) -> ExamResponse:
    """Request hint for current question"""
    logger.info(f"Hint requested - SessionID: {session_id}")

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        hint_data = await exam_service.request_hint()
        logger.info(
            f"Hint provided - SessionID: {session_id}, Hints used: {hint_data['hints_used']}"
        )

        return ExamResponse(
            state=exam_service.state_machine.get_current_state().value,
            message="Hint generated",
            data=hint_data,
        )
    except Exception as e:
        logger.error(f"Failed to generate hint - SessionID: {session_id}, Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/question/{question_id}/evaluation")
async def get_question_evaluation(session_id: str, question_id: str) -> ExamResponse:
    """获取特定问题的评估结果"""
    logger.info(
        f"Question evaluation requested - SessionID: {session_id}, QuestionID: {question_id}"
    )

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        logger.warning(f"Session not found - SessionID: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    evaluation = exam_service.get_question_evaluation(question_id)
    if "error" in evaluation:
        logger.warning(f"Evaluation not found - {evaluation['error']}")
        raise HTTPException(status_code=404, detail=evaluation["error"])

    logger.info(f"Question evaluation retrieved - QuestionID: {question_id}")
    return ExamResponse(
        state=exam_service.state_machine.get_current_state().value,
        message="Question evaluation retrieved successfully",
        data=evaluation,
    )


# WebSocket endpoint
@router.websocket("/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket connection handler for real-time interaction"""
    await websocket.accept()

    exam_service = exam_sessions.get(session_id)
    if not exam_service:
        await websocket.close(code=4000, reason="Session not found")
        return

    try:
        while True:
            try:
                # Receive message
                data = await websocket.receive_json()

                # Process message
                if "answer" in data:
                    # 获取当前状态
                    current_state = exam_service.state_machine.get_current_state()

                    # 根据当前状态选择不同的处理方法
                    if current_state == "CHAT":
                        # 在CHAT状态下使用process_chat_answer方法
                        logger.info(f"WS: Processing chat answer - SessionID: {session_id}")
                        try:
                            result = await exam_service.process_chat_answer(data["answer"])
                        except Exception as e:
                            logger.error(
                                f"WS: Error processing chat answer - SessionID: {session_id}, Error: {str(e)}"
                            )
                            # 如果处理失败，提供一个紧急回退响应
                            result = {
                                "type": "chat",
                                "content": "抱歉，处理您的消息时出现了问题。您可以尝试继续考试或提出一个不同的问题。",
                            }
                    else:
                        # 其他状态使用原有的process_answer方法
                        logger.info(f"WS: Processing regular answer - SessionID: {session_id}")
                        result = await exam_service.process_answer(data["answer"])

                    # If there is a state transition, provide more meaningful messages
                    current_state = exam_service.state_machine.get_current_state().value
                    if current_state == "QUESTIONING":
                        message = "好的，让我们继续考试问题。请认真思考后回答。"
                    elif current_state == "CHAT":
                        message = (
                            "我理解你想休息一下。我们可以简单聊聊，当你准备好继续考试时请告诉我。"
                        )
                    elif current_state == "EXPLAINING":
                        message = "这个概念看起来需要更详细的解释，让我为你澄清一下。"
                    elif current_state == "EVALUATING":
                        message = "考试部分已结束，我将对你的表现进行评估。"
                    elif current_state == "COMPLETED":
                        message = "考试已完成，你可以查看你的评估报告了。"
                    elif current_state == "INIT":
                        message = "请选择一个考试主题开始。"
                    elif current_state == "TOPIC_SELECTED":
                        message = "主题已选择，我们准备开始考试。"
                    else:
                        message = f"当前状态: {current_state}"

                    # Send response
                    await websocket.send_json(
                        {
                            "type": "response",
                            "state": exam_service.state_machine.get_current_state().value,
                            "message": message,
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
