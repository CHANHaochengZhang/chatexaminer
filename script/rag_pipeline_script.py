# %%
# Import required libraries
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from docarray import DocList

# Set OpenAI API key
from dotenv import load_dotenv
from openai import OpenAI
from pdf_load import DocumentMetadata, KnowledgeDoc, db, model

# Configure logging
logging.basicConfig(
    filename="data/rag_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

ROOT_DIR = Path(__file__).parent.parent
env_path = ROOT_DIR / ".env"

print(f"Current working directory: {os.getcwd()}")
print(f"Looking for .env at: {env_path}")

if not env_path.exists():
    raise FileNotFoundError(f".env file not found at {env_path}")

load_dotenv(env_path)
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

# Define project paths
DATA_DIR = ROOT_DIR / "data"
QUESTIONS_FILE = DATA_DIR / "exam_questions.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


# %%
# Define RAG pipeline
@dataclass
class ExamQuestion:
    """Structure for exam questions"""

    question_id: str
    question: str
    context: List[str]
    difficulty: int
    topic: str
    context_metadata: List[Dict[str, any]] = field(default_factory=list)
    approved: bool = False
    teacher_notes: Optional[str] = None


class RAGPipeline:
    def __init__(self, questions_file: Path = QUESTIONS_FILE):
        """Initialize RAG pipeline with specified questions file path"""
        self.questions_file = questions_file
        self.questions = self.load_questions()

    def load_questions(self) -> Dict[str, ExamQuestion]:
        """Load existing questions from JSON file"""
        if self.questions_file.exists():
            with open(self.questions_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {qid: ExamQuestion(**q) for qid, q in data.items()}
        return {}

    def save_questions(self):
        """Save questions to JSON file"""
        # Ensure parent directory exists
        self.questions_file.parent.mkdir(exist_ok=True)

        with open(self.questions_file, "w", encoding="utf-8") as f:
            json.dump(
                {qid: asdict(q) for qid, q in self.questions.items()},
                f,
                indent=2,
                ensure_ascii=False,  # 支持中文等非ASCII字符
            )

    def get_relevant_context(self, question: str, top_k: int = 5) -> List[str]:
        """Improved context retrieval"""
        # Vectorize the question
        question_embedding = model.encode(question)

        # Create query document with metadata
        query_doc = KnowledgeDoc(
            text=question,
            embedding=question_embedding,
            metadata=DocumentMetadata(filename="query", page_number=0, chunk_index=0),
        )

        # Search in VectorDB
        results = db.search(
            inputs=DocList[KnowledgeDoc]([query_doc]),
            limit=top_k * 2,  # Get more results initially for better filtering
        )

        # Enhanced relevance scoring
        scored_contexts = []
        question_keywords = set(question.lower().split())

        for match in results[0].matches:
            text = " ".join(match.text.split())  # Clean text
            # Calculate relevance score
            text_keywords = set(text.lower().split())
            keyword_overlap = len(question_keywords & text_keywords)
            relevance_score = keyword_overlap / len(question_keywords)

            scored_contexts.append(
                {"text": text, "score": relevance_score, "metadata": match.metadata}
            )

        # Sort by relevance and select top_k
        scored_contexts.sort(key=lambda x: x["score"], reverse=True)
        return scored_contexts[:top_k]

    def generate_question(self, topic: str, difficulty: int) -> ExamQuestion:
        """Generate new exam question"""
        # Create prompt for question generation
        prompt = f"""Generate an exam question about {topic} at difficulty level {difficulty}/5.
        The question should be clear, specific, and test deep understanding."""

        # Get relevant context
        contexts = self.get_relevant_context(topic)
        context_text = "\n\n".join(c["text"] for c in contexts)

        # Generate question using GPT-4
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert exam question generator.",
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nRelevant context:\n{context_text}",
                },
            ],
            temperature=0.7,
        )

        # Create question object
        question = ExamQuestion(
            question_id=f"Q{len(self.questions) + 1}",
            question=response.choices[0].message.content.strip(),
            context=[c["text"] for c in contexts],
            context_metadata=[
                {
                    "filename": c["metadata"].filename,
                    "page_number": c["metadata"].page_number,
                    "chunk_index": c["metadata"].chunk_index,
                }
                for c in contexts
            ],  # 添加元数据
            difficulty=difficulty,
            topic=topic,
        )

        # Save to questions dictionary
        self.questions[question.question_id] = question
        self.save_questions()

        return question

    def answer_question(self, question_id: str, student_answer: str) -> str:
        """Evaluate student answer using RAG"""
        if question_id not in self.questions:
            raise ValueError(f"Question {question_id} not found")

        question = self.questions[question_id]
        context_text = "\n\n".join(question.context)

        prompt = f"""Based on the following context and question, evaluate the student's answer:

Context:
{context_text}

Question:
{question.question}

Student Answer:
{student_answer}

Please provide:
1. Score (0-100)
2. Detailed feedback
3. Correct aspects
4. Areas for improvement"""

        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": "You are an expert exam evaluator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()


# %%
# Example usage
if __name__ == "__main__":
    rag = RAGPipeline()

    # Generate new question
    question = rag.generate_question(
        topic="Direct methods for optimal control",
        difficulty=4,
    )
    print(f"Generated Question: {question.question}\n")
    logging.info(f"Generated Question: {question.question}\n")

    # Evaluate answer
    answer = """Direct Collocation Methods
Direct collocation methods are drawing tools used to visualize control problems and help make them easier to solve.

Solving with Sequential Convex Programming (SCP)
First, SCP randomly picks control values, then adjusts state variables to minimize the cost function.

Limitations of Direct Methods
Direct methods are always perfect and have no limitations."""
    logging.info(f"Answer:\n{answer}")

    evaluation = rag.answer_question(question.question_id, answer)
    print(f"Evaluation:\n{evaluation}")
    logging.info(f"Evaluation:\n{evaluation}")
# %%
