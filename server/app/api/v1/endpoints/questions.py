from typing import Any, List

from app.services.rag_service import rag_service
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/generate")
async def generate_question(topic: str, difficulty: int) -> Any:
    try:
        return await rag_service.generate_question(topic, difficulty)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation-tree/{topic}")
async def get_conversation_tree(topic: str, difficulty: int = 1, depth: int = 3) -> Any:
    try:
        return await rag_service.generate_conversation_tree(topic, difficulty, depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
