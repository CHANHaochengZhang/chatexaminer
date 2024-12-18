from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExamQuestion:
    """Structure for exam questions"""

    question_id: str
    question: str
    context: List[str]
    difficulty: int
    topic: str
    subtopic: str
    context_metadata: List[Dict[str, any]] = field(default_factory=list)
    approved: bool = False
    teacher_notes: Optional[str] = None
    expected_answers: Dict[str, Dict[str, str]] = field(
        default_factory=lambda: {
            "correct": {"example": "", "source": ""},
            "partial": {"example": "", "source": ""},
            "incorrect": {"example": "", "source": ""},
        }
    )
