import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.exam import ExamSession
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)


class ExamState(str, Enum):
    INIT = "INIT"
    TOPIC_SELECTED = "TOPIC_SELECTED"
    QUESTIONING = "QUESTIONING"
    EXPLAINING = "EXPLAINING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    PREPARATION = "PREPARATION"
    PAUSED = "PAUSED"
    CHAT = "CHAT"


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
        logger.info("Initializing exam state machine")
        self.current_state: ExamState = ExamState.INIT
        self.context: Dict[str, Any] = {
            "questions_answered": 0,
            "hints_requested": 0,
            "current_difficulty": 3,
            "question_history": [],
            "response_quality": [],
            "topic": None,
            "subtopic": None,
            "exam_session": None,
        }
        self.state_history = []  # 添加状态历史记录列表
        logger.info(f"Initial state: {self.current_state}, context initialized")

        # Define allowed state transitions and conditions
        self.allowed_transitions = {
            ExamState.INIT: [
                (ExamState.PREPARATION, "student_not_ready"),
                (ExamState.TOPIC_SELECTED, "student_ready"),
                (ExamState.CHAT, "casual_conversation"),
            ],
            ExamState.PREPARATION: [
                (ExamState.INIT, "need_more_preparation"),
                (ExamState.TOPIC_SELECTED, "student_ready"),
            ],
            ExamState.TOPIC_SELECTED: [
                (ExamState.QUESTIONING, "start_exam()"),
                (ExamState.CHAT, "casual_conversation"),
            ],
            ExamState.QUESTIONING: [
                (ExamState.EXPLAINING, "student_confused/need_clarification"),
                (ExamState.EVALUATING, "questions_completed"),
                (ExamState.QUESTIONING, "good_response/select_next_question"),
                (ExamState.PAUSED, "student_needs_break"),
                (ExamState.CHAT, "casual_conversation"),
            ],
            ExamState.EXPLAINING: [
                (ExamState.QUESTIONING, "provide_explanation()"),
                (ExamState.CHAT, "casual_conversation"),
            ],
            ExamState.EVALUATING: [
                (ExamState.COMPLETED, "generate_final_evaluation()"),
                (ExamState.CHAT, "casual_conversation"),
            ],
            ExamState.PAUSED: [
                (ExamState.QUESTIONING, "resume_exam"),
                (ExamState.CHAT, "casual_conversation"),
            ],
            ExamState.CHAT: [
                (ExamState.INIT, "return_to_init"),
                (ExamState.TOPIC_SELECTED, "return_to_topic"),
                (ExamState.QUESTIONING, "return_to_question"),
                (ExamState.EXPLAINING, "return_to_explanation"),
                (ExamState.EVALUATING, "return_to_evaluation"),
                (ExamState.PAUSED, "return_to_pause"),
            ],
        }

    def can_transition_to(self, new_state: ExamState) -> bool:
        """Check if transition to new state is allowed"""
        is_valid = any(
            new_state == state for state, _ in self.allowed_transitions[self.current_state]
        )
        logger.debug(
            f"State transition check: {self.current_state} -> {new_state}, valid: {is_valid}"
        )
        return is_valid

    def get_valid_transitions(self) -> List[str]:
        """Get all valid transitions for current state"""
        transitions = [
            f"{state.value} ({condition})"
            for state, condition in self.allowed_transitions[self.current_state]
        ]
        logger.debug(f"Valid transitions for state {self.current_state}: {transitions}")
        return transitions

    def transition(self, new_state: ExamState, metadata: Optional[Dict] = None) -> bool:
        """Execute state transition"""
        logger.info(f"Attempting state transition: {self.current_state} -> {new_state}")
        logger.debug(f"Transition metadata: {metadata}")

        if not self.can_transition_to(new_state):
            error_msg = f"Invalid state transition: {self.current_state} -> {new_state}"
            logger.error(f"{error_msg}\nValid transitions: {self.get_valid_transitions()}")
            raise ValueError(error_msg)

        # Record state transition
        self.state_history.append(
            {
                "from_state": self.current_state,
                "to_state": new_state,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata,
            }
        )

        # Update state
        self.current_state = new_state
        logger.info(f"Current state updated to: {self.current_state}")

        # Update context
        if metadata:
            self._update_context(metadata)
            logger.debug(f"Context updated: {self.context}")

        return True

    def _get_transition_condition(self, new_state: ExamState) -> str:
        """Get transition condition"""
        for state, condition in self.allowed_transitions[self.current_state]:
            if state == new_state:
                return condition
        return "unknown_condition"

    def _update_context(self, metadata: Dict[str, Any]):
        """Update context information"""
        logger.debug(f"Updating context with metadata: {metadata}")
        self.context.update(metadata)

        # Special handling
        if self.current_state == ExamState.TOPIC_SELECTED:
            if "topic" not in metadata or metadata["topic"] is None:
                error_msg = "Topic must be specified when transitioning to TOPIC_SELECTED state"
                logger.error(error_msg)
                raise ValueError(error_msg)
            self.context["topic"] = metadata["topic"]
            self.context["subtopic"] = metadata.get("subtopic")
            logger.info(
                f"Topic set: {self.context['topic']}, subtopic: {self.context.get('subtopic')}"
            )

        elif self.current_state == ExamState.QUESTIONING:
            if "response_quality" in metadata:
                self.context["response_quality"].append(metadata["response_quality"])
                logger.debug(f"Response quality record added: {metadata['response_quality']}")
            self.context["questions_answered"] += 1
            logger.info(f"Questions answered updated to: {self.context['questions_answered']}")

        elif self.current_state == ExamState.EXPLAINING:
            self.context["hints_requested"] += 1
            logger.info(f"Hints requested updated to: {self.context['hints_requested']}")

    def get_current_state(self) -> ExamState:
        """Get current state"""
        logger.debug(f"Getting current state: {self.current_state}")
        return self.current_state

    def get_context(self) -> Dict[str, Any]:
        """Get current context"""
        logger.debug(f"Getting current context: {self.context}")
        return self.context

    def start_exam(self, topic: str, questions_file: Path):
        """Start new exam session"""
        logger.info(f"Starting new exam with topic: {topic}")

        if self.current_state != ExamState.TOPIC_SELECTED:
            error_msg = (
                f"Cannot start exam: current state {self.current_state} is not TOPIC_SELECTED"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Create exam session
        self.context["exam_session"] = ExamSession.create_session(
            topic=topic, questions_file=questions_file
        )
        logger.info("Exam session created successfully")

        # Transition to QUESTIONING state
        self.transition(ExamState.QUESTIONING)
        logger.info("Transitioned to QUESTIONING state")

    def get_current_question(self) -> Optional[Dict]:
        """Get current question without advancing index"""
        logger.debug(f"Attempting to get current question, state: {self.current_state}")

        if self.current_state != ExamState.QUESTIONING:
            logger.debug(f"Current state {self.current_state} is not QUESTIONING, returning None")
            return None

        session = self.context.get("exam_session")
        if not session:
            logger.warning("No exam session found")
            return None

        # 改用 get_current_question
        question = session.get_current_question()
        if question:
            logger.info(
                f"Retrieved current question: ID={question.get('question_id')}, difficulty={question.get('difficulty')}"
            )
        else:
            logger.info("No more questions available")
        return question

    def increase_difficulty(self):
        """Increase current question difficulty"""
        if self.context.get("current_difficulty"):
            old_difficulty = self.context["current_difficulty"]
            self.context["current_difficulty"] = min(5, old_difficulty + 1)
            logger.info(
                f"Difficulty increased: {old_difficulty} -> {self.context['current_difficulty']}"
            )

    def decrease_difficulty(self):
        """Decrease current question difficulty"""
        if self.context.get("current_difficulty"):
            old_difficulty = self.context["current_difficulty"]
            self.context["current_difficulty"] = max(1, old_difficulty - 1)
            logger.info(
                f"Difficulty decreased: {old_difficulty} -> {self.context['current_difficulty']}"
            )
