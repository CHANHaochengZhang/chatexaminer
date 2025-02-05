import json
import logging
from typing import Dict, List

import openai
from app.models.evaluation import EvaluationMetrics, ExamEvaluation, QuestionEvaluation

# 配置日志
logger = logging.getLogger(__name__)


class EvaluationService:
    def __init__(self):
        self.current_evaluation = ExamEvaluation()

    async def evaluate_response(
        self, question: Dict, student_response: str, hints_used: int, time_taken: float
    ) -> QuestionEvaluation:
        """Evaluate a single response"""
        logger.info(f"\n{'='*50}\n评估新的回答\n{'='*50}")
        logger.info(f"问题ID: {question['question_id']}")
        logger.info(f"问题难度: {question['difficulty']}")
        logger.info(f"学生回答: {student_response[:100]}...")  # 只记录前100个字符
        logger.info(f"使用提示次数: {hints_used}")
        logger.info(f"回答用时: {time_taken:.2f}秒")

        # Prepare prompt for GPT evaluation
        prompt = f"""Evaluate this student's answer based on the following criteria:

Question: {question['question']}
Expected Answer: {question['expected_answers']['correct']['example']}
Relevant Context: {question['context']}
Student's Answer: {student_response}

Please evaluate on three metrics (0-100):
1. Accuracy: How correct is the answer?
2. Clarity: How well is it expressed?
3. Understanding: How well does the student understand the concept? is it fit context?

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

        # 记录评分结果
        logger.info("\n评分结果:")
        logger.info(f"准确性(Accuracy): {eval_result['accuracy']}/100")
        logger.info(f"清晰度(Clarity): {eval_result['clarity']}/100")
        logger.info(f"理解度(Understanding): {eval_result['understanding']}/100")
        logger.info(f"反馈: {eval_result['feedback']}")

        # 计算平均分
        avg_score = (
            eval_result["accuracy"] + eval_result["clarity"] + eval_result["understanding"]
        ) / 3
        logger.info(f"平均分: {avg_score:.2f}/100")
        logger.info(f"{'='*50}\n")

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
