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
    context_metadata: List[Dict[str, any]] = field(default_factory=list)
    approved: bool = False
    teacher_notes: Optional[str] = None
