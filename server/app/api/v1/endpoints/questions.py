from typing import Any, List, Optional

from app.services.rag_service import rag_service
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class QuestionRequest(BaseModel):
    topic: str
    difficulty: str = "medium"  # easy, medium, hard
    num_questions: int = 1
    context_length: Optional[int] = 500


class QuestionResponse(BaseModel):
    question_id: str
    question: str
    topic: str
    difficulty: str
    context: str
    suggested_answer: Optional[str]


@router.post("/generate", response_model=List[QuestionResponse])
async def generate_questions(request: QuestionRequest):
    """Generate questions based on a specific topic"""
    try:
        return await rag_service.generate_questions(
            request.topic,
            request.difficulty,
            request.num_questions,
            request.context_length,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics", response_model=List[str])
async def get_available_topics():
    """Get all available topics"""
    try:
        return await rag_service.get_available_topics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
