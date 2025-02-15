import json
import random
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

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
    topic: str
    current_question_index: int = 0
    questions: List[Dict] = []
    student_answers: Dict[str, str] = {}
    evaluations: Dict[str, Dict] = {}
    question_history: List[str] = []  # 记录所有问过的问题ID

    @classmethod
    def create_session(cls, topic: str, questions_file: Path) -> "ExamSession":
        """Create a new exam session"""
        # Load questions file
        with open(questions_file, "r", encoding="utf-8") as f:
            all_questions = json.load(f)

        # Filter questions related to the topic
        topic_questions = [q for q in all_questions.values() if topic.lower() in q["topic"].lower()]

        # Sort by difficulty
        topic_questions.sort(key=lambda x: x["difficulty"])

        return cls(topic=topic, questions=topic_questions)

    def get_current_question(self) -> Optional[Dict]:
        """Get the current question without advancing the index"""
        if self.current_question_index >= len(self.questions):
            return None
        return self.questions[self.current_question_index]

    def get_next_question(self) -> Optional[Dict]:
        """Get the next question and advance the index"""
        if self.current_question_index >= len(self.questions):
            return None

        question = self.questions[self.current_question_index]
        # 记录问题ID到历史记录
        if question and question["question_id"] not in self.question_history:
            self.question_history.append(question["question_id"])

        self.current_question_index += 1
        return question

    def get_prev_question(self) -> Optional[Dict]:
        """Get the previous question for evaluation"""
        if not self.question_history:
            return None
        # 获取最后一个问过的问题ID
        last_question_id = self.question_history[-1] if self.question_history else None
        if last_question_id:
            # 在问题列表中查找这个ID对应的问题
            for question in self.questions:
                if question["question_id"] == last_question_id:
                    return question
        return None

    def record_answer(self, question_id: str, answer: str):
        """Record student's answer for a question"""
        self.student_answers[question_id] = answer

    def record_evaluation(self, question_id: str, evaluation: Dict):
        """Record evaluation results for an answer"""
        self.evaluations[question_id] = evaluation
