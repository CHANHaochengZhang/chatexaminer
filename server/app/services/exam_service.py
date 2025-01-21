import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import openai
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
        # Add function calling definition for state detection
        self.state_detection_functions = [
            {
                "name": "determine_state",
                "description": "Determine the next state based on student's response",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "next_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                            "description": "The next state to transition to",
                        },
                        "confidence": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5,
                            "description": "Confidence level in state determination",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for choosing this state",
                        },
                    },
                    "required": ["next_state", "confidence", "reason"],
                },
            }
        ]

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

    async def detect_state(self, response: str, current_state: ExamState) -> Dict:
        """Detect next state based on student's response using AI"""
        # Create a serializable version of session metrics
        serializable_metrics = {
            "questions_answered": self.session_metrics["questions_answered"],
            "hints_requested": self.session_metrics["hints_requested"],
            "response_consistency": self.session_metrics["response_consistency"],
        }

        system_prompt = """You are an AI exam state analyzer. Determine the next state based on the student's response.

State Machine Rules:
1. INIT -> TOPIC_SELECTED: When student greets or shows readiness
2. TOPIC_SELECTED -> QUESTIONING: When student indicates readiness to start exam
3. QUESTIONING -> EXPLAINING: When student shows confusion
4. QUESTIONING -> CHAT: When student gives meaningless/random answers
5. EXPLAINING -> QUESTIONING: Only after student confirms understanding
6. EXPLAINING -> CHAT: When student is not engaging seriously
7. QUESTIONING -> QUESTIONING: After normal response
8. QUESTIONING -> EVALUATING: When completed

Key indicators for CHAT state:
- Meaningless responses (e.g., "hehe", "???", random characters)
- Off-topic responses
- Non-serious engagement
- Random keyboard input
- Repeated short/meaningless answers

For QUESTIONING state:
- Move to CHAT if:
  * Student gives meaningless answers (e.g., "hehe", "???", random letters)
  * Student is not engaging with the question
  * Response is completely off-topic
  * Response shows no attempt to answer academically
- Stay in QUESTIONING if the answer is relevant to the question
- Move to EXPLAINING if student shows confusion"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""Current state: {current_state}
Student response: "{response}"
Context: {json.dumps(serializable_metrics)}

Determine the next state based on this response.""",
            },
        ]

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=self.state_detection_functions,
            function_call={"name": "determine_state"},
        )

        result = json.loads(response.choices[0].message.function_call.arguments)
        return result

    async def process_answer(self, answer: str) -> Dict:
        """Process student's answer and return next interaction"""
        # First detect the next state using AI
        current_state = self.state_machine.get_current_state()
        state_result = await self.detect_state(answer, current_state)
        next_state = ExamState(state_result["next_state"])

        # Record previous state before transition
        if next_state == ExamState.CHAT:
            self.state_machine.context["previous_state"] = current_state

        # Special handling for TOPIC_SELECTED state
        if current_state == ExamState.TOPIC_SELECTED:
            if next_state == ExamState.QUESTIONING:
                # Only start exam if transitioning to QUESTIONING
                self.exam_start_time = time.time()
                return {"type": "state_change", "state": next_state.value}
            else:
                # If not ready (e.g., "maybe", "not sure"), transition to CHAT
                self.state_machine.transition(ExamState.CHAT)
                return {
                    "type": "state_change",
                    "state": ExamState.CHAT.value,
                    "content": "Let's chat until you feel ready to start the exam.",
                }

        # Transition to the detected state
        self.state_machine.transition(next_state)

        # If transitioning to EVALUATING, generate final evaluation
        if next_state == ExamState.EVALUATING:
            if self.exam_start_time is None:
                self.exam_start_time = time.time()  # Set start time if not set
            return {
                "type": "complete",
                "content": "Exam ended, generating evaluation report...",
                "evaluation": self._generate_final_evaluation(),
            }

        # If in QUESTIONING state, process the answer
        if current_state == ExamState.QUESTIONING and self.state_machine.context.get(
            "exam_session"
        ):
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

            # Update topic coverage and behavior metrics
            self._update_topic_progress(
                current_question["topic"],
                evaluation.metrics.understanding,
                [],
            )
            self._update_behavior_metrics(time_taken)
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
