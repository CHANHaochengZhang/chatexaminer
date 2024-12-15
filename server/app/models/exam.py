from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ExamState(Enum):
    INIT = "init"
    TOPIC_SELECTED = "topic_selected"
    QUESTIONING = "questioning"
    EXPLAINING = "explaining"
    EVALUATING = "evaluating"
    COMPLETED = "completed"


class StudentResponse(BaseModel):
    intention: int
    evaluation: int
    response_text: str


class ExamSession(BaseModel):
    id: str
    topic: str
    current_question_index: int
    responses: List[StudentResponse]
    current_state: ExamState
    difficulty_level: int
