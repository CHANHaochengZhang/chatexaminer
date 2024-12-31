from app.api.v1.endpoints import answers, conversations, knowledge, questions
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(answers.router, prefix="/answers", tags=["answers"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
