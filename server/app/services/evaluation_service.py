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
        logger.info(f"\n{'='*50}\nEvaluate new answer\n{'='*50}")
        logger.info(f"Question ID: {question['question_id']}")
        logger.info(f"Question: {question['question']}")
        logger.info(f"Question Difficulty: {question['difficulty']}")
        logger.info(
            f"Student's Answer: {student_response[:100]}..."
        )  # Only record the first 100 characters
        logger.info(f"Hints Used: {hints_used}")
        logger.info(f"Answer Time: {time_taken:.2f} seconds")

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

        # Calculate average score
        avg_score = (
            eval_result["accuracy"] + eval_result["clarity"] + eval_result["understanding"]
        ) / 3
        logger.info(f"Average Score: {avg_score:.2f}/100")
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
            question=question["question"],
            topic=question["topic"],
            metrics=metrics,
            feedback=eval_result["feedback"],
            difficulty=question["difficulty"],
            time_taken=time_taken,
            raw_response=student_response,
            level=eval_result["level"],
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
        raw_response: str = "",
        question: str = "",
        topic: str = "",
        level: str = "",
    ):
        """Add question evaluation"""
        print(
            f"Adding question evaluation: ID={question_id}, Metrics={metrics}, Time taken={time_taken}s"
        )
        self.current_evaluation.question_evaluations[question_id] = QuestionEvaluation(
            question_id=question_id,
            question=question,
            topic=topic,
            metrics=metrics,
            time_taken=time_taken,
            difficulty=difficulty,
            feedback=feedback,
            raw_response=raw_response,
            level=level,
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

            # Apply difficulty weight
            question_score = base_score * difficulty_weights[eval.difficulty]

            # Deduct points for hints used (each hint deducts 5% of base score)
            hint_penalty = (base_score * 0.05) * eval.metrics.hints_used
            question_score -= hint_penalty

            # Ensure score is not below 0 or above 100
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

    async def generate_final_evaluation(self) -> None:
        """Generate final evaluation by reviewing all question evaluations"""
        # Prepare evaluation data for all questions
        evaluation_history = []
        for q_eval in self.current_evaluation.question_evaluations.values():
            evaluation_history.append(
                {
                    "question": q_eval.question,
                    "student_response": q_eval.raw_response,
                    "metrics": {
                        "accuracy": q_eval.metrics.accuracy,
                        "clarity": q_eval.metrics.clarity,
                        "understanding": q_eval.metrics.understanding,
                        "hints_used": q_eval.metrics.hints_used,
                    },
                    "feedback": q_eval.feedback,
                    "level": q_eval.level,
                    "difficulty": q_eval.difficulty,
                }
            )

        # Prepare prompt
        prompt = f"""As a professional oral examiner, please provide a comprehensive final evaluation based on the student's responses.

Please analyze the following aspects:
1. Overall Performance
   - Evaluate the student's mastery of concepts
   - Assess their ability to express ideas clearly
   - Consider their depth of understanding
   - Note any patterns in their responses

2. Knowledge Assessment
   - Accuracy of technical concepts
   - Completeness of explanations
   - Logical coherence of answers
   - Use of appropriate terminology

3. Response Quality
   - Clarity and organization of thoughts
   - Ability to handle questions of varying difficulty
   - Consistency across different topics
   - Response to hints when provided

Based on the evaluation history below, please provide:
1. A final score (0-100)
2. An overall evaluation level (Excellent/Good/Fair/Poor)
3. Detailed feedback including strengths and areas for improvement

Evaluation History:
{json.dumps(evaluation_history, indent=2)}

Please format your response as JSON with the following structure:
{{
    "final_score": float,
    "final_level": "string",
    "final_feedback": "string"
}}
"""

        # Get evaluation from GPT
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert oral examiner providing final evaluation.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        # Parse response
        final_eval = json.loads(response.choices[0].message.content)

        # Update evaluation result
        self.current_evaluation.final_score = final_eval["final_score"]
        self.current_evaluation.final_level = final_eval["final_level"]
        self.current_evaluation.final_feedback = final_eval["final_feedback"]

        # Record final evaluation result
        logger.info("\nFinal Evaluation Results:")
        logger.info(f"Final Score: {final_eval['final_score']}/100")
        logger.info(f"Overall Level: {final_eval['final_level']}")
        logger.info(f"Detailed Feedback: {final_eval['final_feedback']}")
        logger.info(f"{'='*50}\n")

    def get_final_evaluation(self) -> ExamEvaluation:
        """Get final evaluation result"""
        return self.current_evaluation
