from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ExamState(str, Enum):
    INIT = "INIT"
    TOPIC_SELECTED = "TOPIC_SELECTED"
    QUESTIONING = "QUESTIONING"
    EXPLAINING = "EXPLAINING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    PREPARATION = "PREPARATION"  # 新增状态


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
        }

        # 定义允许的状态转换和条件
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
            ],
            ExamState.EXPLAINING: [(ExamState.QUESTIONING, "provide_explanation()")],
            ExamState.EVALUATING: [
                (ExamState.COMPLETED, "generate_final_evaluation()")
            ],
        }

    def can_transition_to(self, new_state: ExamState) -> bool:
        """检查是否允许转换到新状态"""
        return any(
            new_state == state
            for state, _ in self.allowed_transitions[self.current_state]
        )

    def get_valid_transitions(self) -> List[str]:
        """获取当前状态下所有有效的转换"""
        return [
            f"{state.value} ({condition})"
            for state, condition in self.allowed_transitions[self.current_state]
        ]

    def transition(self, new_state: ExamState, metadata: Optional[Dict] = None) -> bool:
        """执行状态转换"""
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition from {self.current_state} to {new_state}\n"
                f"Valid transitions: {self.get_valid_transitions()}"
            )

        # 记录转换
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            condition=self._get_transition_condition(new_state),
            metadata=metadata,
        )

        # 更新状态
        self.current_state = new_state

        # 更新上下文
        if metadata:
            self._update_context(metadata)

        return True

    def _get_transition_condition(self, new_state: ExamState) -> str:
        """获取转换条件"""
        for state, condition in self.allowed_transitions[self.current_state]:
            if state == new_state:
                return condition
        return "unknown_condition"

    def _update_context(self, metadata: Dict[str, Any]):
        """更新上下文信息"""
        self.context.update(metadata)

        # 特殊处理
        if self.current_state == ExamState.QUESTIONING:
            if "response_quality" in metadata:
                self.context["response_quality"].append(metadata["response_quality"])
            self.context["questions_answered"] += 1

        elif self.current_state == ExamState.EXPLAINING:
            self.context["hints_requested"] += 1

    def get_current_state(self) -> ExamState:
        """获取当前状态"""
        return self.current_state

    def get_context(self) -> Dict[str, Any]:
        """获取当前上下文"""
        return self.context
