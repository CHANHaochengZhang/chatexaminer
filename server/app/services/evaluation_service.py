from typing import Dict, List
import openai
from app.models.evaluation import EvaluationMetrics, QuestionEvaluation, ExamEvaluation
import json

class EvaluationService:
    def __init__(self):
        self.current_evaluation = ExamEvaluation()
    
    async def evaluate_response(
        self, 
        question: Dict, 
        student_response: str,
        hints_used: int,
        time_taken: float
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
                {"role": "system", "content": "You are an expert evaluator for oral examinations."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        # Parse response
        eval_result = json.loads(response.choices[0].message.content)
        
        # Create evaluation metrics
        metrics = EvaluationMetrics(
            accuracy=eval_result["accuracy"],
            clarity=eval_result["clarity"],
            understanding=eval_result["understanding"],
            hints_used=hints_used
        )
        
        # Create question evaluation
        evaluation = QuestionEvaluation(
            question_id=question["question_id"],
            metrics=metrics,
            feedback=eval_result["feedback"],
            difficulty=question["difficulty"],
            time_taken=time_taken,
            raw_response=student_response
        )
        
        # Update exam evaluation
        self.current_evaluation.question_evaluations[question["question_id"]] = evaluation
        
        return evaluation
    
    def update_topic_coverage(self, topic: str, score: float, covered_points: List[str] = None):
        """Update topic coverage scores"""
        self.current_evaluation.topic_coverage[topic] = score
    
    def update_behavior_score(self, metrics: Dict[str, float]):
        """Update behavior score based on examination metrics"""
        # Calculate behavior score based on:
        # - Average response time
        # - Hint usage frequency
        # - Response consistency
        behavior_score = 100.0
        
        if metrics.get("avg_hints_per_question", 0) > 2:
            behavior_score -= 20
            
        if metrics.get("avg_time_per_question", 0) > 300:  # 5 minutes
            behavior_score -= 20
            
        self.current_evaluation.behavior_score = behavior_score
    
    def get_final_evaluation(self) -> ExamEvaluation:
        """Generate final evaluation report"""
        self.current_evaluation.calculate_total_score()
        return self.current_evaluation 