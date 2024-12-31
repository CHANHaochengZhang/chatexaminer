from typing import Any, List, Optional

from app.services.rag_service import rag_service
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AnswerRequest(BaseModel):
    question_id: str
    student_answer: str
    max_score: Optional[int] = 100


class AnswerResponse(BaseModel):
    question_id: str
    score: int
    feedback: str
    correct_answer: str
    improvement_suggestions: List[str]


class AnswerFeedbackRequest(BaseModel):
    question_id: str
    student_answer: str
    teacher_feedback: str


@router.post("/evaluate", response_model=AnswerResponse)
async def evaluate_answer(request: AnswerRequest):
    """Evaluate a student's answer"""
    try:
        return await rag_service.evaluate_answer(request.question_id, request.student_answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback", response_model=AnswerResponse)
async def provide_feedback(request: AnswerFeedbackRequest):
    """Provide additional feedback"""
    try:
        return await rag_service.provide_feedback(
            request.question_id, request.student_answer, request.teacher_feedback
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
