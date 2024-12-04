from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class Message(BaseModel):
    role: str  # system, user, assistant
    content: str
    timestamp: datetime


class ConversationRequest(BaseModel):
    question_id: str
    message: str
    context_length: Optional[int] = 1000


class ConversationResponse(BaseModel):
    question_id: str
    messages: List[Message]
    suggestions: List[str]


@router.post("/chat", response_model=ConversationResponse)
async def continue_conversation(request: ConversationRequest):
    """Continue the conversation about a specific question"""
    pass


@router.get("/history/{question_id}", response_model=List[Message])
async def get_conversation_history(question_id: str):
    """Get the conversation history for a specific question"""
    pass
