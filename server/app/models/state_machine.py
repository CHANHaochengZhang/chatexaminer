from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from pydantic import BaseModel
from app.models.exam import ExamSession


class ExamState(str, Enum):
    INIT = "INIT"
    TOPIC_SELECTED = "TOPIC_SELECTED"
    QUESTIONING = "QUESTIONING"
    EXPLAINING = "EXPLAINING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    PREPARATION = "PREPARATION"
    PAUSED = "PAUSED"


class StateTransition(BaseModel):
    from_state: ExamState
    to_state: ExamState
    condition: str
    metadata: Optional[Dict[str, Any]] = None


class StateResponse(BaseModel):
    next_state: ExamState
    confidence: int
    reason: str


class ExamStateMachine:
    def __init__(self):
        self.current_state: ExamState = ExamState.INIT
        self.context: Dict[str, Any] = {
            "questions_answered": 0,
            "hints_requested": 0,
            "current_difficulty": 3,
            "question_history": [],
            "response_quality": [],
            "topic": None,
            "subtopic": None,
            "exam_session": None
        }

        # Define allowed state transitions and conditions
        self.allowed_transitions = {
            ExamState.INIT: [
                (ExamState.PREPARATION, "student_not_ready"),
                (ExamState.TOPIC_SELECTED, "student_ready"),
            ],
            ExamState.PREPARATION: [
                (ExamState.INIT, "need_more_preparation"),
                (ExamState.TOPIC_SELECTED, "student_ready"),
            ],
            ExamState.TOPIC_SELECTED: [(ExamState.QUESTIONING, "start_exam()")],
            ExamState.QUESTIONING: [
                (ExamState.EXPLAINING, "student_confused/need_clarification"),
                (ExamState.EVALUATING, "questions_completed"),
                (ExamState.QUESTIONING, "good_response/select_next_question"),
                (ExamState.PAUSED, "student_needs_break"),
            ],
            ExamState.EXPLAINING: [(ExamState.QUESTIONING, "provide_explanation()")],
            ExamState.EVALUATING: [
                (ExamState.COMPLETED, "generate_final_evaluation()")
            ],
            ExamState.PAUSED: [
                (ExamState.QUESTIONING, "resume_exam"),
            ],
        }

    def can_transition_to(self, new_state: ExamState) -> bool:
        """Check if transition to new state is allowed"""
        return any(
            new_state == state
            for state, _ in self.allowed_transitions[self.current_state]
        )

    def get_valid_transitions(self) -> List[str]:
        """Get all valid transitions for the current state"""
        return [
            f"{state.value} ({condition})"
            for state, condition in self.allowed_transitions[self.current_state]
        ]

    def transition(self, new_state: ExamState, metadata: Optional[Dict] = None) -> bool:
        """Execute state transition"""
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition from {self.current_state} to {new_state}\n"
                f"Valid transitions: {self.get_valid_transitions()}"
            )

        # Record transition
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            condition=self._get_transition_condition(new_state),
            metadata=metadata,
        )

        # Update state
        self.current_state = new_state

        # Update context
        if metadata:
            self._update_context(metadata)

        return True

    def _get_transition_condition(self, new_state: ExamState) -> str:
        """Get transition condition"""
        for state, condition in self.allowed_transitions[self.current_state]:
            if state == new_state:
                return condition
        return "unknown_condition"

    def _update_context(self, metadata: Dict[str, Any]):
        """Update context information"""
        self.context.update(metadata)

        # Special handling
        if self.current_state == ExamState.TOPIC_SELECTED:
            # Ensure topic is set
            if "topic" not in metadata or metadata["topic"] is None:
                raise ValueError(
                    "Topic must be specified when transitioning to TOPIC_SELECTED state"
                )
            self.context["topic"] = metadata["topic"]
            self.context["subtopic"] = metadata.get("subtopic")

        elif self.current_state == ExamState.QUESTIONING:
            if "response_quality" in metadata:
                self.context["response_quality"].append(metadata["response_quality"])
            self.context["questions_answered"] += 1

        elif self.current_state == ExamState.EXPLAINING:
            self.context["hints_requested"] += 1

    def get_current_state(self) -> ExamState:
        """Get current state"""
        return self.current_state

    def get_context(self) -> Dict[str, Any]:
        """Get current context"""
        return self.context

    def start_exam(self, topic: str, questions_file: Path):
        """开始新的考试会话"""
        if self.current_state != ExamState.TOPIC_SELECTED:
            raise ValueError("Must be in TOPIC_SELECTED state to start exam")
            
        # 创建考试会话
        self.context["exam_session"] = ExamSession.create_session(
            topic=topic,
            questions_file=questions_file
        )
        
        # 转换到 QUESTIONING 状态
        self.transition(ExamState.QUESTIONING)
        
    def get_current_question(self) -> Optional[Dict]:
        """获取当前问题"""
        if self.current_state != ExamState.QUESTIONING:
            return None
            
        session = self.context.get("exam_session")
        if not session:
            return None
            
        return session.get_next_question()

    def increase_difficulty(self):
        """增加当前问题难度"""
        if self.context.get("current_difficulty"):
            self.context["current_difficulty"] = min(5, self.context["current_difficulty"] + 1)

    def decrease_difficulty(self):
        """降低当前问题难度"""
        if self.context.get("current_difficulty"):
            self.context["current_difficulty"] = max(1, self.context["current_difficulty"] - 1)
