import json
from typing import Dict, List

import openai
from app.models.evaluation import EvaluationMetrics, ExamEvaluation, QuestionEvaluation


class EvaluationService:
    def __init__(self):
        self.current_evaluation = ExamEvaluation()

    async def evaluate_response(
        self, question: Dict, student_response: str, hints_used: int, time_taken: float
    ) -> QuestionEvaluation:
        """Evaluate a single response"""

        # Prepare prompt for GPT evaluation
        prompt = f"""Evaluate this student's answer based on the following criteria:

Question: {question['question']}
Expected Answer: {question['expected_answers']['correct']['example']}
Student's Answer: {student_response}

Please evaluate on three metrics (0-100):
1. Accuracy: How correct is the answer?
2. Clarity: How well is it expressed?
3. Understanding: How well does the student understand the concept?

Provide brief feedback explaining the evaluation.

Format your response as JSON:
{{
    "accuracy": <score>,
    "clarity": <score>,
    "understanding": <score>,
    "feedback": "<feedback>"
}}"""

        # Get evaluation from GPT
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert evaluator for oral examinations.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        # Parse response
        eval_result = json.loads(response.choices[0].message.content)

        # Create evaluation metrics
        metrics = EvaluationMetrics(
            accuracy=eval_result["accuracy"],
            clarity=eval_result["clarity"],
            understanding=eval_result["understanding"],
            hints_used=hints_used,
        )

        # Create question evaluation
        evaluation = QuestionEvaluation(
            question_id=question["question_id"],
            metrics=metrics,
            feedback=eval_result["feedback"],
            difficulty=question["difficulty"],
            time_taken=time_taken,
            raw_response=student_response,
        )

        # Update exam evaluation
        self.current_evaluation.question_evaluations[question["question_id"]] = evaluation

        return evaluation

    def add_question_evaluation(
        self,
        question_id: str,
        metrics: EvaluationMetrics,
        time_taken: float,
        difficulty: int,
        feedback: str = "",
    ):
        """Add question evaluation"""
        print(
            f"Adding question evaluation: ID={question_id}, Metrics={metrics}, Time taken={time_taken}s"
        )
        self.current_evaluation.question_evaluations[question_id] = QuestionEvaluation(
            question_id=question_id,
            metrics=metrics,
            time_taken=time_taken,
            difficulty=difficulty,
            feedback=feedback,
            raw_response="",
        )

        # Update total score
        total_score = 0
        for eval in self.current_evaluation.question_evaluations.values():
            # Calculate question score (average of accuracy, clarity, and understanding)
            question_score = (
                eval.metrics.accuracy + eval.metrics.clarity + eval.metrics.understanding
            ) / 3
            # Apply difficulty weight
            question_score *= eval.difficulty / 5
            # Deduct points for hints used
            question_score -= eval.metrics.hints_used * 10
            total_score += question_score

        # Calculate average score
        self.current_evaluation.total_score = total_score / len(
            self.current_evaluation.question_evaluations
        )
        print(f"Updated total score: {self.current_evaluation.total_score}")

    def update_topic_coverage(self, topic: str, coverage_score: float, covered_points: List[str]):
        """Update topic coverage"""
        self.current_evaluation.topic_coverage[topic] = coverage_score

    def update_behavior_score(self, metrics: Dict[str, float]):
        """Update behavior score"""
        # Calculate behavior score based on metrics
        behavior_score = (
            (1 - metrics["avg_hints_per_question"] * 0.1)  # Reduce score for hint usage
            * metrics["response_consistency"]  # Impact of answer consistency
            * (1 - min(1, metrics["avg_time_per_question"] / 300))  # Time impact (max 300s)
        )
        self.current_evaluation.behavior_score = behavior_score * 100  # Convert to percentage

    def get_final_evaluation(self) -> ExamEvaluation:
        """Get final evaluation result"""
        return self.current_evaluation
