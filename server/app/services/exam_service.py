from pathlib import Path
from typing import Optional, Dict
from app.models.state_machine import ExamStateMachine, ExamState
from app.models.exam import ExamSession
from app.core.config import settings

class ExamService:
    def __init__(self):
        self.state_machine = ExamStateMachine()
        self.questions_file = Path(settings.QUESTIONS_FILE)
    
    def start_exam(self, topic: str) -> Dict:
        """开始考试"""
        if not self.questions_file.exists():
            raise FileNotFoundError("Questions file not found")
            
        self.state_machine.start_exam(topic, self.questions_file)
        return self.get_next_interaction()
    
    def get_next_interaction(self) -> Dict:
        """获取下一个交互内容"""
        state = self.state_machine.get_current_state()
        
        if state == ExamState.QUESTIONING:
            question = self.state_machine.get_current_question()
            if question:
                return {
                    "type": "question",
                    "content": question["question"],
                    "question_id": question["question_id"],
                    "difficulty": question["difficulty"]
                }
            else:
                # 所有问题已完成，转到评估状态
                self.state_machine.transition(ExamState.EVALUATING)
                return {
                    "type": "complete",
                    "content": "考试完成，正在生成评估报告..."
                }
                
        return {
            "type": "state_change",
            "state": state.value
        } 

    def process_answer(self, answer: str) -> Dict:
        """处理学生答案并返回下一个交互"""
        if not self.state_machine.context.get("exam_session"):
            raise ValueError("No active exam session")
        
        session = self.state_machine.context["exam_session"]
        current_question = session.questions[session.current_question_index - 1]
        
        # 记录答案
        session.record_answer(current_question["question_id"], answer)
        
        # TODO: 这里可以添加答案评估逻辑
        
        return self.get_next_interaction()

