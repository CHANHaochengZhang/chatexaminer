from typing import Any

from app.services.rag_service import rag_service
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/{question_id}/evaluate")
async def evaluate_answer(question_id: str, answer: str) -> Any:
    try:
        return await rag_service.evaluate_answer(question_id, answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
