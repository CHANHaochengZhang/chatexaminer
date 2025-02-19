from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class QuestionRecord(BaseModel):
    """单个问题的记录"""

    sequence: int
    question: Dict
    student_response: Dict[str, str]
    evaluation: Optional[Dict] = None
    hints: List[Dict] = []
    time_taken: float = 0.0


class ExamMetadata(BaseModel):
    """考试元数据"""

    session_id: str
    timestamp: str
    student_type: str
    topic: str
    total_duration: float
    state_history: List[Dict]


class StatisticalMetrics(BaseModel):
    """统计指标"""

    difficulty_distribution: Dict[str, int]
    topic_distribution: Dict[str, int]
    performance_trends: Dict[str, List[float]]


class ExamRecord(BaseModel):
    """完整的考试记录"""

    exam_metadata: ExamMetadata
    questions_and_answers: List[QuestionRecord]
    final_evaluation: Dict
    statistical_metrics: StatisticalMetrics

    @classmethod
    def create_from_exam_session(cls, exam_service) -> "ExamRecord":
        """从考试会话创建记录"""
        # 创建元数据
        metadata = ExamMetadata(
            session_id=exam_service.session_id,
            timestamp=datetime.now().isoformat(),
            student_type=getattr(exam_service, "student_type", "unknown"),
            topic=exam_service.state_machine.context.get("topic", ""),
            total_duration=exam_service.session_metrics.get("total_time", 0.0),
            state_history=exam_service.state_machine.state_history,
        )

        # 创建问题记录列表
        questions_and_answers = []
        for idx, question in enumerate(exam_service.session.questions):
            q_id = question["question_id"]
            question_record = QuestionRecord(
                sequence=idx + 1,
                question=question,
                student_response={
                    "content": exam_service.session.student_answers.get(q_id, ""),
                    "timestamp": datetime.now().isoformat(),
                    "hints_requested": exam_service.session_metrics.get("hints_requested", 0),
                },
                evaluation=exam_service.session.evaluations.get(q_id),
                time_taken=exam_service.session_metrics.get(f"time_taken_{q_id}", 0.0),
            )
            questions_and_answers.append(question_record)

        # 获取最终评估
        final_evaluation = exam_service.evaluation_service.get_final_evaluation().dict()

        # 计算统计指标
        statistical_metrics = StatisticalMetrics(
            difficulty_distribution={
                "easy": len([q for q in exam_service.session.questions if q["difficulty"] <= 2]),
                "medium": len(
                    [q for q in exam_service.session.questions if 2 < q["difficulty"] <= 4]
                ),
                "hard": len([q for q in exam_service.session.questions if q["difficulty"] > 4]),
            },
            topic_distribution={
                topic: len([q for q in exam_service.session.questions if q["topic"] == topic])
                for topic in set(q["topic"] for q in exam_service.session.questions)
            },
            performance_trends={
                "score_progression": [
                    eval.get("score", 0.0) for eval in exam_service.session.evaluations.values()
                ],
                "time_progression": [
                    eval.get("time_taken", 0.0)
                    for eval in exam_service.session.evaluations.values()
                ],
                "hints_progression": [
                    eval.get("hints_used", 0) for eval in exam_service.session.evaluations.values()
                ],
            },
        )

        return cls(
            exam_metadata=metadata,
            questions_and_answers=questions_and_answers,
            final_evaluation=final_evaluation,
            statistical_metrics=statistical_metrics,
        )

    def save_to_file(self, directory: str = "exam_records"):
        """保存记录到文件"""
        import json
        import os

        # 确保目录存在
        os.makedirs(directory, exist_ok=True)

        # 生成文件名
        filename = f"{directory}/{self.exam_metadata.session_id}.json"

        # 保存为JSON文件
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.dict(), f, ensure_ascii=False, indent=2)

        return filename

    @classmethod
    def load_from_file(cls, filename: str) -> "ExamRecord":
        """从文件加载记录"""
        import json

        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(**data)
