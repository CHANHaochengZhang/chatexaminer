# %%
# Import required libraries
import json
import logging
import os
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from docarray import DocList

# Set OpenAI API key
from dotenv import load_dotenv
from openai import OpenAI
from pdf_load import DocumentMetadata, KnowledgeDoc, db, model

# Define project paths
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
QUESTIONS_FILE = DATA_DIR / "exam_questions.json"

# Ensure data and log directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=LOG_DIR / "rag_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

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

    def get_broad_context(self, topic: str, top_k: int = 15) -> List[Dict[str, Any]]:
        """First round search: Get broad context related to the topic"""
        topic_embedding = model.encode(topic)
        query_doc = KnowledgeDoc(
            text=topic,
            embedding=topic_embedding,
            metadata=DocumentMetadata(filename="query", page_number=0, chunk_index=0),
        )

        results = db.search(
            inputs=DocList[KnowledgeDoc]([query_doc]),
            limit=top_k,
        )

        broad_contexts = [
            {"text": match.text, "metadata": match.metadata}
            for match in results[0].matches
        ]

        # Log broad contexts
        logging.info(f"Broad contexts for topic '{topic}': {broad_contexts}")

        return broad_contexts

    def focused_search(
        self, selected_context: Dict[str, Any], top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Second round search: Get focused context based on selected content and ensure continuity"""
        context_embedding = model.encode(selected_context["text"])
        query_doc = KnowledgeDoc(
            text=selected_context["text"],
            embedding=context_embedding,
            metadata=DocumentMetadata(filename="query", page_number=0, chunk_index=0),
        )

        # Get initial results
        results = db.search(
            inputs=DocList[KnowledgeDoc]([query_doc]),
            limit=top_k * 2,  # Get more results initially to find continuous chunks
        )

        # Group contexts by file and page
        grouped_contexts = {}
        for match in results[0].matches:
            key = (match.metadata.filename, match.metadata.page_number)
            if key not in grouped_contexts:
                grouped_contexts[key] = []
            grouped_contexts[key].append(
                {
                    "text": match.text,
                    "metadata": match.metadata,
                    "chunk_index": match.metadata.chunk_index,
                }
            )

        # Find continuous chunks
        continuous_contexts = []
        for contexts in grouped_contexts.values():
            # Sort by chunk index
            contexts.sort(key=lambda x: x["chunk_index"])

            # Find continuous sequences
            current_sequence = []
            for i, context in enumerate(contexts):
                if not current_sequence:
                    current_sequence.append(context)
                elif context["chunk_index"] == current_sequence[-1]["chunk_index"] + 1:
                    current_sequence.append(context)
                else:
                    # If sequence breaks, store if it's the longest so far
                    if len(current_sequence) > len(continuous_contexts):
                        continuous_contexts = current_sequence
                    current_sequence = [context]

            # Check final sequence
            if len(current_sequence) > len(continuous_contexts):
                continuous_contexts = current_sequence

        # Take up to top_k continuous contexts
        focused_contexts = continuous_contexts[:top_k]

        # Log focused contexts
        logging.info(f"Selected continuous contexts: {focused_contexts}")
        logging.info(f"Chunks selected: {[c['chunk_index'] for c in focused_contexts]}")

        return focused_contexts

    def generate_question(self, topic: str, difficulty: int) -> ExamQuestion:
        """Generate new exam question using continuous context chunks"""
        # First round: Get broad context
        broad_contexts = self.get_broad_context(topic, top_k=15)

        # Enhanced filtering with scoring
        topic_keywords = set(topic.lower().split())
        scored_contexts = []

        for context in broad_contexts:
            # Calculate relevance score
            context_text = context["text"].lower()
            keyword_matches = sum(
                1 for keyword in topic_keywords if keyword in context_text
            )
            score = keyword_matches / len(topic_keywords)

            scored_contexts.append(
                {
                    "text": context["text"],
                    "metadata": context["metadata"],
                    "score": score,
                }
            )

        # Sort by relevance
        scored_contexts.sort(key=lambda x: x["score"], reverse=True)
        if not scored_contexts:
            raise ValueError(f"No relevant contexts found for topic '{topic}'")

        # Get continuous focused contexts
        best_context = scored_contexts[0]  # 保存最佳上下文
        focused_contexts = self.focused_search(best_context)

        # Combine continuous contexts
        context_text = "\n".join(c["text"] for c in focused_contexts)

        # Enhanced prompt for specific question generation
        prompt = f"""Based on the following specific context, generate a precise and focused exam question related to the topic '{topic}'.

Topic: {topic}
Difficulty: {difficulty}/5
Selected Content: {best_context['text'][:200]}...

Requirements:
1. Focus on a single, specific concept, formula, or relationship related to the topic
2. Question must be answerable using ONLY the provided context
3. Maximum length: 15 words
4. Avoid broad questions like "describe" or "explain in detail"
5. Instead of asking "What is X?", ask about:
   - Specific components or parameters
   - Mathematical meanings of symbols
   - Units of measurement
   - Specific relationships between concepts
   - Concrete applications or examples
   - Step-by-step procedures
   - Specific conditions or constraints

Context for reference:
{context_text}

Generate a focused question that tests understanding of a specific aspect from the selected content."""

        # Generate question using GPT-4
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at generating precise, focused exam questions. Avoid broad, open-ended questions.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
        )

        # Create question object
        question = ExamQuestion(
            question_id=f"Q{len(self.questions) + 1}",
            question=response.choices[0].message.content.strip(),
            context=[c["text"] for c in focused_contexts],
            context_metadata=[
                {
                    "filename": c["metadata"].filename,
                    "page_number": c["metadata"].page_number,
                    "chunk_index": c["metadata"].chunk_index,
                    "selected_context": best_context["text"][:200],  # 使用best_context
                }
                for c in focused_contexts
            ],
            difficulty=difficulty,
            topic=topic,
        )

        self.questions[question.question_id] = question
        self.save_questions()

        return question

    def answer_question(self, question_id: str, student_answer: str) -> str:
        """Evaluate student answer using RAG"""
        if question_id not in self.questions:
            raise ValueError(f"Question {question_id} not found")

        question = self.questions[question_id]
        context_text = "\n\n".join(question.context)

        prompt = f"""Evaluate the student's answer based on the following context and question:

Context:
{context_text}

Question:
{question.question}

Student Answer:
{student_answer}

Please provide:
1. Score (0-100)
2. Detailed feedback, focusing on clarity and relevance
3. Correct aspects of the student's answer
4. Specific areas for improvement, with suggestions for better responses"""

        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": "You are an expert exam evaluator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content.strip()


# %%
# Example usage
if __name__ == "__main__":
    rag = RAGPipeline()

    # Generate new question
    # question = rag.generate_question(
    #     topic="Direct methods for optimal control",
    #     difficulty=1,
    # )
    # print(f"Generated Question: {question.question}\n")
    # logging.info(f"Generated Question: {question.question}\n")
    for i in range(10):
        difficulty = (i % 5) + 1
        question = rag.generate_question(
            topic="Direct Methods for Optimal Control - Continuous-Time Control Problem and Discrete Optimization using Trapezoid Collocation",
            difficulty=difficulty,
        )
        print(f"Generated Question (Difficulty {difficulty}): {question.question}\n")
        logging.info(
            f"Generated Question (Difficulty {difficulty}): {question.question}\n"
        )

    # Evaluate answer
#     answer = """Direct Collocation Methods
# Direct collocation methods are drawing tools used to visualize control problems and help make them easier to solve.

# Solving with Sequential Convex Programming (SCP)
# First, SCP randomly picks control values, then adjusts state variables to minimize the cost function.

# Limitations of Direct Methods
# Direct methods are always perfect and have no limitations."""
#     logging.info(f"Answer:\n{answer}")

#     evaluation = rag.answer_question(question.question_id, answer)
#     print(f"Evaluation:\n{evaluation}")
#     logging.info(f"Evaluation:\n{evaluation}")
# %%
