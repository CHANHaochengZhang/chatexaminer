from app.api.v1.endpoints import answers, questions
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(answers.router, prefix="/answers", tags=["answers"])
