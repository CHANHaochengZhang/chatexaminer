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
        logger.info(f"问题: {question['question']}")
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

First, determine if the answer directly addresses the question asked:
1. Does the answer specifically address the question about "general form of a non-linear optimization problem"?
2. Is the answer relevant to the specific question, not just the general topic?
3. Does the answer contain the key mathematical or formal components expected?

Then evaluate on three metrics (0-100):
1. Accuracy: How correctly does the answer address the specific question asked? (Not just general topic knowledge)
2. Clarity: How well is the answer expressed and structured?
3. Understanding: How well does the student demonstrate understanding of the specific concept asked in the question?

Based on both relevance and quality, provide a single word to describe the overall quality:
- "Excellent": Directly answers the question with comprehensive understanding (80-100)
- "Good": Answers the question with solid understanding, minor gaps (65-79)
- "Fair": Partially answers the question or shows tangential understanding (50-64)
- "Poor": Does not answer the question or shows significant misunderstanding (0-49)

Note: An answer that demonstrates good knowledge but does not address the specific question should receive a lower score.

Provide brief feedback explaining:
1. Whether the answer addresses the specific question
2. What key elements are missing or incorrect
3. Suggestions for improvement

Question: {question['question']}
Student's Answer: {student_response}

Format your response as JSON:
{{
    "level": "<single_word_evaluation>",
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
        logger.info(f"总体评价(Level): {eval_result['level']}")
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
            # Calculate base question score (average of accuracy, clarity, and understanding)
            base_score = (
                eval.metrics.accuracy + eval.metrics.clarity + eval.metrics.understanding
            ) / 3

            # Apply difficulty weight
            difficulty_weights = {1: 0.7, 2: 0.85, 3: 1.0, 4: 1.2, 5: 1.5}

            # 应用难度权重
            question_score = base_score * difficulty_weights[eval.difficulty]

            # Deduct points for hints used (每个提示扣除基础分数的5%)
            hint_penalty = (base_score * 0.05) * eval.metrics.hints_used
            question_score -= hint_penalty

            # 确保分数不会低于0或超过100
            question_score = max(0, min(100, question_score))

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
