import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).parent.parent.parent.parent
SCRIPT_DIR = ROOT_DIR / "script"
sys.path.append(str(ROOT_DIR))
sys.path.append(str(SCRIPT_DIR))

from app.core.config import settings
from conversation_tree_generator import ConversationTreeGenerator
from rag_pipeline_script import RAGPipeline


class RAGService:
    def __init__(self):
        self.rag_pipeline = RAGPipeline(
            questions_file=settings.DATA_DIR / "exam_questions.json"
        )
        self.tree_generator = ConversationTreeGenerator()

    async def generate_question(self, topic: str, difficulty: int):
        return self.rag_pipeline.generate_question(topic, difficulty)

    async def evaluate_answer(self, question_id: str, answer: str):
        return self.rag_pipeline.answer_question(question_id, answer)

    async def generate_conversation_tree(
        self, topic: str, base_difficulty: int, depth: int = 3
    ):
        return self.tree_generator.generate_tree(topic, base_difficulty, depth)


rag_service = RAGService()
