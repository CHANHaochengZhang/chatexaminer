from app.models.exam import StudentResponse
from app.services.exam_service import ExamService
from fastapi import APIRouter, Depends

router = APIRouter()


@router.post("/exam/{session_id}/response")
async def process_student_response(
    session_id: str, response: str, exam_service: ExamService = Depends()
):
    return await exam_service.process_response(session_id, response)
