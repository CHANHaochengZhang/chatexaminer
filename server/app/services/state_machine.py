from app.models.exam import ExamSession, ExamState
from app.services.assistant import AssistantService
from app.services.rag_service import rag_service


class ExamStateMachine:
    def __init__(self):
        self.assistant = AssistantService()
        self.rag = rag_service

    async def process_response(self, session: ExamSession, response: str) -> ExamState:
        if session.current_state == ExamState.QUESTIONING:
            student_response = await self.assistant.process_response(
                response=response, context=self._get_context(session)
            )

            session.responses.append(student_response)

            return self._determine_next_state(session, student_response)
