import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI
from sentence_transformers import SentenceTransformer
from vectordb import InMemoryExactNNVectorDB


@dataclass
class ExamContext:
    """Exam context information"""

    subject: str
    difficulty_level: int
    previous_questions: List[str]
    previous_answers: List[str]
    current_topic: str


@dataclass
class RAGResponse:
    """RAG response structure"""

    question: str
    context: str
    confidence_score: float
    knowledge_sources: List[str]


class ExaminerRAG:
    def __init__(self, knowledge_base_path: Path):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.db = InMemoryExactNNVectorDB[KnowledgeDoc]()
        self.load_knowledge_base(knowledge_base_path)

    def load_knowledge_base(self, path: Path):
        """Load and initialize knowledge base"""
        # Implement knowledge base loading logic
        pass

    def generate_question(self, exam_context: ExamContext) -> RAGResponse:
        """Generate exam question"""
        # 1. Retrieve relevant knowledge
        relevant_docs = self._retrieve_knowledge(exam_context)

        # 2. Generate question
        question = self._generate_question_from_context(relevant_docs, exam_context)

        return question

    def evaluate_answer(
        self, question: str, student_answer: str, exam_context: ExamContext
    ) -> Dict:
        """Evaluate student's answer"""
        # 1. Retrieve relevant knowledge
        relevant_docs = self._retrieve_knowledge_for_evaluation(
            question, student_answer
        )

        # 2. Evaluate answer
        evaluation = self._evaluate_with_context(
            question, student_answer, relevant_docs, exam_context
        )

        return evaluation

    def _retrieve_knowledge(self, exam_context: ExamContext) -> List[str]:
        """Retrieve relevant knowledge"""
        query_embedding = self.model.encode(
            f"{exam_context.current_topic} {exam_context.subject}"
        )
        results = self.db.search(
            query_embedding,
            limit=5,
            filter_criteria={"difficulty": exam_context.difficulty_level},
        )
        return results

    def _generate_question_from_context(
        self, relevant_docs: List[str], exam_context: ExamContext
    ) -> RAGResponse:
        """Generate question based on context"""
        prompt = self._create_question_prompt(relevant_docs, exam_context)

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional examiner who needs to generate in-depth exam questions based on provided knowledge.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        return self._parse_response(response)

    def _evaluate_with_context(
        self,
        question: str,
        student_answer: str,
        relevant_docs: List[str],
        exam_context: ExamContext,
    ) -> Dict:
        """Evaluate student's answer"""
        prompt = self._create_evaluation_prompt(
            question, student_answer, relevant_docs, exam_context
        )

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional examiner who needs to evaluate student answers based on knowledge base content.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        return self._parse_evaluation(response)

    def _create_question_prompt(
        self, relevant_docs: List[str], exam_context: ExamContext
    ) -> str:
        """Create prompt for question generation"""
        previous_questions = (
            exam_context.previous_questions[-3:]
            if exam_context.previous_questions
            else "None"
        )

        prompt = (
            "Generate an exam question based on the following knowledge base content:\n\n"
            f"Knowledge Base Content:\n{chr(10).join(relevant_docs)}\n\n"
            "Exam Context:\n"
            f"- Subject: {exam_context.subject}\n"
            f"- Current Topic: {exam_context.current_topic}\n"
            f"- Difficulty Level: {exam_context.difficulty_level}\n"
            f"- Previous Questions: {previous_questions}\n\n"
            "Requirements:\n"
            "1. Question must be based on provided knowledge base content\n"
            "2. Must match current topic and difficulty level\n"
            "3. Avoid repeating previous questions\n"
            "4. Question should have depth to test student understanding\n"
            "5. Question should be clear and unambiguous\n\n"
            "Please generate the question:"
        )
        return prompt

    def _create_evaluation_prompt(
        self,
        question: str,
        student_answer: str,
        relevant_docs: List[str],
        exam_context: ExamContext,
    ) -> str:
        """Create prompt for evaluation"""
        prompt = (
            "Please evaluate the student's answer:\n\n"
            f"Question: {question}\n\n"
            f"Student's Answer: {student_answer}\n\n"
            f"Reference Knowledge:\n{chr(10).join(relevant_docs)}\n\n"
            "Evaluation Requirements:\n"
            "1. Accuracy: Does the answer align with knowledge base content\n"
            "2. Completeness: Does it cover all aspects of the question\n"
            "3. Depth of Understanding: Does it demonstrate deep concept comprehension\n"
            "4. Clarity: Is the answer well-structured and clear\n\n"
            "Please provide:\n"
            "1. Score (0-100)\n"
            "2. Detailed evaluation\n"
            "3. Suggestions for improvement"
        )
        return prompt
