from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    accuracy: float = Field(0.0, ge=0.0, le=100.0)
    clarity: float = Field(0.0, ge=0.0, le=100.0)
    understanding: float = Field(0.0, ge=0.0, le=100.0)
    hints_used: int = 0


class QuestionEvaluation(BaseModel):
    question_id: str
    question: str
    topic: str
    metrics: EvaluationMetrics
    feedback: str
    difficulty: int
    time_taken: float  # in seconds
    raw_response: str


class ExamEvaluation(BaseModel):
    total_score: float = 0.0
    question_evaluations: Dict[str, QuestionEvaluation] = {}
    topic_coverage: Dict[str, float] = {}
    behavior_score: float = 0.0
    final_feedback: str = ""

    def calculate_total_score(self) -> float:
        """Calculate final score based on components"""
        if not self.question_evaluations:
            return 0.0

        # Calculate individual questions score (60%)
        question_scores = []
        for eval in self.question_evaluations.values():
            metrics = eval.metrics
            # Average of metrics
            question_score = (metrics.accuracy + metrics.clarity + metrics.understanding) / 3
            # Apply hint penalty
            question_score -= metrics.hints_used * 10
            # Weight by difficulty
            question_score *= eval.difficulty / 5
            question_scores.append(question_score)

        avg_question_score = sum(question_scores) / len(question_scores)
        question_component = avg_question_score * 0.6

        # Topic coverage score (20%)
        topic_score = sum(self.topic_coverage.values()) / len(self.topic_coverage) * 20

        # Behavior score (20%)
        behavior_component = self.behavior_score * 0.2

        self.total_score = question_component + topic_score + behavior_component
        return self.total_score
