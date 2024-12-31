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
        self.topic_key_points = {}  # 存储每个主题的关键点
        self.session_metrics = {
            "questions_answered": 0,
            "hints_requested": 0,
            "response_consistency": 1.0,
            "topic_progress": {},
        }

    async def start_exam(self, topic: str) -> Dict:
        """开始考试"""
        if not self.questions_file.exists():
            raise FileNotFoundError("Questions file not found")

        # 验证话题是否有效
        with open(self.questions_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
            valid_topics = {q["topic"] for q in questions.values()}

        if topic not in valid_topics:
            raise ValueError(
                f"Invalid topic. Available topics: {', '.join(valid_topics)}"
            )

        # 初始化考试会话
        self.exam_start_time = time.time()
        self.current_topic = topic
        self.state_machine.start_exam(topic, self.questions_file)

        # 从问题文件中提取主题关键点
        self._extract_topic_key_points(topic)

        # 记录开始时间
        self.question_start_time = time.time()

        return self.get_next_interaction()

    def _extract_topic_key_points(self, topic: str):
        """从问题文件中提取主题的关键点"""
        with open(self.questions_file, "r", encoding="utf-8") as f:
            questions = json.load(f)

        topic_questions = [q for q in questions.values() if q["topic"] == topic]
        key_points = set()

        for q in topic_questions:
            # 从正确答案中提取关键点
            correct_answer = q["expected_answers"]["correct"]["example"]
            # 这里可以使用更复杂的NLP方法来提取关键点
            # 简单示例：将句子分割并提取关键短语
            points = [p.strip() for p in correct_answer.split(".") if p.strip()]
            key_points.update(points)

        self.topic_key_points[topic] = list(key_points)

    def get_next_interaction(self) -> Dict:
        """获取下一个交互内容"""
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
                    "context": question.get("context", []),  # 提供上下文供参考
                    "topic": question["topic"],
                }
            else:
                # 所有问题已完成，生成最终评估
                final_evaluation = self._generate_final_evaluation()
                self.state_machine.transition(ExamState.EVALUATING)
                return {
                    "type": "complete",
                    "content": "考试完成，正在生成评估报告...",
                    "evaluation": final_evaluation,
                }

        return {"type": "state_change", "state": state.value}

    async def process_answer(self, answer: str) -> Dict:
        """处理学生答案并返回下一个交互"""
        # 检查是否要结束考试
        if answer.lower() in ["exit", "quit", "end", "stop", "i want to end the exam"]:
            self.state_machine.transition(ExamState.EVALUATING)
            return {
                "type": "complete",
                "content": "考试结束，正在生成评估报告...",
                "evaluation": self._generate_final_evaluation(),
            }

        if not self.state_machine.context.get("exam_session"):
            raise ValueError("No active exam session")

        session = self.state_machine.context["exam_session"]
        current_question = session.questions[session.current_question_index - 1]

        # 更新会话指标
        self.session_metrics["questions_answered"] += 1

        # 计算本次回答的时间
        time_taken = time.time() - self.question_start_time

        # 评估答案
        evaluation = await self.evaluation_service.evaluate_response(
            question=current_question,
            student_response=answer,
            hints_used=self.session_metrics["hints_requested"],
            time_taken=time_taken,
        )

        # 记录答案和评估
        session.record_answer(current_question["question_id"], answer)
        session.record_evaluation(current_question["question_id"], evaluation.dict())

        # 更新主题覆盖度
        self._update_topic_progress(
            current_question["topic"],
            evaluation.metrics.understanding,
            [],  # 使用空列表替代 key_points_covered
        )

        # 更新行为指标
        self._update_behavior_metrics(time_taken)

        # 检查是否需要调整难度
        self._adjust_difficulty(evaluation.metrics)

        return self.get_next_interaction()

    def _update_topic_progress(
        self, topic: str, understanding_score: float, covered_points: List[str]
    ):
        """更新主题进度"""
        if topic not in self.session_metrics["topic_progress"]:
            self.session_metrics["topic_progress"][topic] = {
                "scores": [],
                "covered_points": set(),
                "total_points": len(self.topic_key_points.get(topic, [])),
            }

        progress = self.session_metrics["topic_progress"][topic]
        progress["scores"].append(understanding_score)
        progress["covered_points"].update(covered_points)

        # 更新评估服务中的主题覆盖度
        self.evaluation_service.update_topic_coverage(
            topic,
            sum(progress["scores"]) / len(progress["scores"]),
            list(progress["covered_points"]),
        )

    def _update_behavior_metrics(self, time_taken: float):
        """更新行为指标"""
        metrics = {
            "avg_hints_per_question": self.session_metrics["hints_requested"]
            / self.session_metrics["questions_answered"],
            "avg_time_per_question": time_taken,
            "response_consistency": self._calculate_response_consistency(),
        }

        self.evaluation_service.update_behavior_score(metrics)

    def _calculate_response_consistency(self) -> float:
        """计算答题一致性"""
        if self.session_metrics["questions_answered"] < 2:
            return 1.0

        session = self.state_machine.context["exam_session"]
        evaluations = [
            eval["metrics"]["understanding"] for eval in session.evaluations.values()
        ]

        # 计算相邻评分的差异
        differences = [
            abs(evaluations[i] - evaluations[i - 1]) for i in range(1, len(evaluations))
        ]

        # 返回一致性分数 (1 - 平均差异/100)
        avg_diff = sum(differences) / len(differences)
        return max(0, 1 - (avg_diff / 100))

    def _adjust_difficulty(self, metrics: EvaluationMetrics):
        """根据学生表现调整问题难度"""
        avg_performance = (metrics.accuracy + metrics.understanding) / 2

        if avg_performance > 85:
            self.state_machine.increase_difficulty()
        elif avg_performance < 60:
            self.state_machine.decrease_difficulty()

    def request_hint(self) -> str:
        """请求提示"""
        self.session_metrics["hints_requested"] += 1
        current_question = self.state_machine.get_current_question()

        # 这里可以实现更智能的提示生成逻辑
        return f"考虑问题的上下文：{' '.join(current_question['context'][:1])}"

    def _generate_final_evaluation(self) -> Dict:
        """生成最终评估报告"""
        final_eval = self.evaluation_service.get_final_evaluation()

        # 添加额外的评估信息
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
