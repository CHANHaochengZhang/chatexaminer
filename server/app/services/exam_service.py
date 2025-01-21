import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings
from app.models.evaluation import EvaluationMetrics
from app.models.exam import ExamSession
from app.models.state_machine import ExamState, ExamStateMachine
from app.services.evaluation_service import EvaluationService


class ExamService:
    def __init__(self):
        self.state_machine = ExamStateMachine()
        self.questions_file = Path(settings.QUESTIONS_FILE)
        self.evaluation_service = EvaluationService()
        self.exam_start_time = None
        self.question_start_time = None
        self.current_topic = None
        self.topic_key_points = {}  # Store key points for each topic
        self.session_metrics = {
            "questions_answered": 0,
            "hints_requested": 0,
            "response_consistency": 1.0,
            "topic_progress": {},
        }

    async def start_exam(self, topic: str) -> Dict:
        """Start the exam"""
        if not self.questions_file.exists():
            raise FileNotFoundError("Questions file not found")

        # Validate if topic is valid
        with open(self.questions_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
            valid_topics = {q["topic"] for q in questions.values()}

        if topic not in valid_topics:
            raise ValueError(f"Invalid topic. Available topics: {', '.join(valid_topics)}")

        # Initialize exam session
        self.exam_start_time = time.time()
        self.current_topic = topic
        self.state_machine.start_exam(topic, self.questions_file)

        # Extract topic key points from questions file
        self._extract_topic_key_points(topic)

        # Record start time
        self.question_start_time = time.time()

        return self.get_next_interaction()

    def _extract_topic_key_points(self, topic: str):
        """Extract key points for the topic from questions file"""
        with open(self.questions_file, "r", encoding="utf-8") as f:
            questions = json.load(f)

        topic_questions = [q for q in questions.values() if q["topic"] == topic]
        key_points = set()

        for q in topic_questions:
            # Extract key points from correct answers
            correct_answer = q["expected_answers"]["correct"]["example"]
            # More complex NLP methods could be used here to extract key points
            # Simple example: split sentences and extract key phrases
            points = [p.strip() for p in correct_answer.split(".") if p.strip()]
            key_points.update(points)

        self.topic_key_points[topic] = list(key_points)

    def get_next_interaction(self) -> Dict:
        """Get next interaction content"""
        state = self.state_machine.get_current_state()

        if state == ExamState.QUESTIONING:
            question = self.state_machine.get_current_question()
            if question:
                self.question_start_time = time.time()
                return {
                    "type": "question",
                    "content": question["question"],
                    "question_id": question["question_id"],
                    "difficulty": question["difficulty"],
                    "context": question.get("context", []),  # Provide context for reference
                    "topic": question["topic"],
                }
            else:
                # All questions completed, generate final evaluation
                final_evaluation = self._generate_final_evaluation()
                self.state_machine.transition(ExamState.EVALUATING)
                return {
                    "type": "complete",
                    "content": "Exam completed, generating evaluation report...",
                    "evaluation": final_evaluation,
                }

        return {"type": "state_change", "state": state.value}

    async def process_answer(self, answer: str) -> Dict:
        """Process student's answer and return next interaction"""
        # Check if exam should end
        if answer.lower() in ["exit", "quit", "end", "stop", "i want to end the exam"]:
            self.state_machine.transition(ExamState.EVALUATING)
            return {
                "type": "complete",
                "content": "Exam ended, generating evaluation report...",
                "evaluation": self._generate_final_evaluation(),
            }

        if not self.state_machine.context.get("exam_session"):
            raise ValueError("No active exam session")

        session = self.state_machine.context["exam_session"]
        current_question = session.questions[session.current_question_index - 1]

        # Update session metrics
        self.session_metrics["questions_answered"] += 1

        # Calculate time taken for this answer
        time_taken = time.time() - self.question_start_time

        # Evaluate answer
        evaluation = await self.evaluation_service.evaluate_response(
            question=current_question,
            student_response=answer,
            hints_used=self.session_metrics["hints_requested"],
            time_taken=time_taken,
        )

        # Record answer and evaluation
        session.record_answer(current_question["question_id"], answer)
        session.record_evaluation(current_question["question_id"], evaluation.dict())

        # Update topic coverage
        self._update_topic_progress(
            current_question["topic"],
            evaluation.metrics.understanding,
            [],  # Using empty list instead of key_points_covered
        )

        # Update behavior metrics
        self._update_behavior_metrics(time_taken)

        # Check if difficulty adjustment is needed
        self._adjust_difficulty(evaluation.metrics)

        return self.get_next_interaction()

    def _update_topic_progress(
        self, topic: str, understanding_score: float, covered_points: List[str]
    ):
        """Update topic progress"""
        if topic not in self.session_metrics["topic_progress"]:
            self.session_metrics["topic_progress"][topic] = {
                "scores": [],
                "covered_points": set(),
                "total_points": len(self.topic_key_points.get(topic, [])),
            }

        progress = self.session_metrics["topic_progress"][topic]
        progress["scores"].append(understanding_score)
        progress["covered_points"].update(covered_points)

        # Update topic coverage in evaluation service
        self.evaluation_service.update_topic_coverage(
            topic,
            sum(progress["scores"]) / len(progress["scores"]),
            list(progress["covered_points"]),
        )

    def _update_behavior_metrics(self, time_taken: float):
        """Update behavior metrics"""
        metrics = {
            "avg_hints_per_question": self.session_metrics["hints_requested"]
            / self.session_metrics["questions_answered"],
            "avg_time_per_question": time_taken,
            "response_consistency": self._calculate_response_consistency(),
        }

        self.evaluation_service.update_behavior_score(metrics)

    def _calculate_response_consistency(self) -> float:
        """Calculate response consistency"""
        if self.session_metrics["questions_answered"] < 2:
            return 1.0

        session = self.state_machine.context["exam_session"]
        evaluations = [eval["metrics"]["understanding"] for eval in session.evaluations.values()]

        # Calculate differences between adjacent scores
        differences = [abs(evaluations[i] - evaluations[i - 1]) for i in range(1, len(evaluations))]

        # Return consistency score (1 - average difference/100)
        avg_diff = sum(differences) / len(differences)
        return max(0, 1 - (avg_diff / 100))

    def _adjust_difficulty(self, metrics: EvaluationMetrics):
        """Adjust difficulty based on student performance"""
        avg_performance = (metrics.accuracy + metrics.understanding) / 2

        if avg_performance > 85:
            self.state_machine.increase_difficulty()
        elif avg_performance < 60:
            self.state_machine.decrease_difficulty()

    def request_hint(self) -> str:
        """Request a hint"""
        self.session_metrics["hints_requested"] += 1
        current_question = self.state_machine.get_current_question()

        # More intelligent hint generation logic could be implemented here
        return f"Consider the question context: {' '.join(current_question['context'][:1])}"

    def _generate_final_evaluation(self) -> Dict:
        """Generate final evaluation report"""
        final_eval = self.evaluation_service.get_final_evaluation()

        # Add additional evaluation information
        return {
            "total_score": final_eval.total_score,
            "topic_coverage": final_eval.topic_coverage,
            "behavior_score": final_eval.behavior_score,
            "question_evaluations": {
                qid: {
                    "score": eval.metrics.dict(),
                    "feedback": eval.feedback,
                    "time_taken": eval.time_taken,
                }
                for qid, eval in final_eval.question_evaluations.items()
            },
            "session_metrics": {
                "total_time": time.time() - self.exam_start_time,
                "questions_answered": self.session_metrics["questions_answered"],
                "hints_used": self.session_metrics["hints_requested"],
                "response_consistency": self.session_metrics["response_consistency"],
            },
        }
