# %%
# Import required libraries
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root directory to Python path
SERVER_DIR = Path(__file__).parent.parent.parent  # Adjust based on project structure
sys.path.append(str(SERVER_DIR))

from app.models.question import ExamQuestion
from docarray import DocList

# Set OpenAI API key
from dotenv import load_dotenv
from openai import OpenAI
from pdf_load import DocumentMetadata, KnowledgeDoc, db, model

# Define project paths
ROOT_DIR = Path(__file__).parent.parent.parent.parent
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
class RAGPipeline:
    def __init__(self, questions_file: Path = QUESTIONS_FILE):
        """Initialize RAG pipeline with specified questions file path"""
        self.questions_file = questions_file
        self.questions = self.load_questions()

    def load_questions(self) -> Dict[str, ExamQuestion]:
        """Load existing questions from JSON file"""
        if self.questions_file.exists():
            try:
                with open(self.questions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Add default subtopic if missing
                    for q in data.values():
                        if "subtopic" not in q:
                            q["subtopic"] = ""  # Empty string as default
                    return {qid: ExamQuestion(**q) for qid, q in data.items()}
            except json.JSONDecodeError:
                return {}
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
                ensure_ascii=False,  # Support non-ASCII characters
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

    def generate_questions_for_topic(
        self, topic: str, num_subtopics: int = 5
    ) -> List[ExamQuestion]:
        """Generate questions for a topic"""
        questions = []
        broad_contexts = self.get_broad_context(
            topic, top_k=num_subtopics * 3
        )  # Get more contexts initially

        print(f"Broad contexts: {broad_contexts}")

        # Ensure contexts are sufficiently different
        filtered_contexts = []
        used_texts = set()

        for context in broad_contexts:
            # Use first 100 characters as a unique identifier
            text_key = context["text"][:100]
            if text_key not in used_texts:
                used_texts.add(text_key)
                filtered_contexts.append(context)
                if len(filtered_contexts) >= num_subtopics:
                    break

        broad_contexts = filtered_contexts

        # If not enough filtered contexts, pad with different ones
        if len(broad_contexts) < num_subtopics:
            remaining_contexts = [
                c for c in broad_contexts if c not in filtered_contexts
            ]
            broad_contexts.extend(
                remaining_contexts[: num_subtopics - len(broad_contexts)]
            )

        print(f"Filtered contexts: {broad_contexts}")

        # Generate questions for each subtopic
        for i in range(min(len(broad_contexts), num_subtopics)):
            selected_context = broad_contexts[i]
            subtopic = f"{topic} - Subtopic {i+1}: {selected_context['text'][:50]}..."
            print(f"Processing {subtopic}")

            # Generate questions for each difficulty level
            for difficulty in range(1, 6):  # Changed range to 1-5
                question = self.generate_question(
                    topic=topic,
                    subtopic=subtopic,
                    difficulty=difficulty,
                    context=selected_context,
                )
                questions.append(question)

        return questions

    def generate_question(
        self, topic: str, subtopic: str, difficulty: int, context: Dict[str, Any]
    ) -> ExamQuestion:
        """Generate a single question"""
        # Use the provided context
        selected_context = context

        # Add filename and page number information
        source_info = f"Source: {selected_context['metadata'].filename}, Page {selected_context['metadata'].page_number}"

        # Retrieve focused contexts
        focused_contexts = self.focused_search(selected_context)

        # Combine context texts
        context_text = "\n".join(c["text"] for c in focused_contexts)

        # Enhanced prompt for specific question generation
        prompt = f"""Based on the following specific context, generate a precise and focused exam question related to the topic '{topic}'.

Topic: {topic}
Difficulty: {difficulty}/5
Selected Content: {selected_context['text'][:200]}...

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

        # Generate answers prompt
        answer_prompt = f"""Question: {response.choices[0].message.content.strip()}

Context:
{selected_context["text"]}

{source_info}

Learning objective: Understand {topic.lower()}

Generate three student answer examples that:
- Use concepts directly from the textbook
- Reflect typical student understanding levels
- Keep answers within 2-3 sentences
- Reference specific content from {source_info}

Format as JSON:
{{
    "correct": {{
        "example": "complete answer with all key points",
        "source": "{source_info}"
    }},
    "partial": {{
        "example": "answer with some correct points but missing critical details",
        "source": "{source_info}"
    }},
    "incorrect": {{
        "example": "answer showing common misconception",
        "source": "{source_info}"
    }}
}}"""

        # Generate answers
        answer_response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at generating example answers. Always respond in valid JSON format.",
                },
                {
                    "role": "user",
                    "content": answer_prompt,
                },
            ],
            temperature=0.7,
        )

        # Parse answers
        try:
            response_content = answer_response.choices[0].message.content.strip()
            logging.info(f"GPT Response: {response_content}")
            expected_answers = json.loads(response_content)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            # Provide default answer structure
            expected_answers = {
                "correct": {"example": "Default correct answer", "source": source_info},
                "partial": {"example": "Default partial answer", "source": source_info},
                "incorrect": {
                    "example": "Default incorrect answer",
                    "source": source_info,
                },
            }

        # Create question object with expected answers
        question = ExamQuestion(
            question_id=f"Q{len(self.questions) + 1}",
            question=response.choices[0].message.content.strip(),
            context=[c["text"] for c in focused_contexts],
            difficulty=difficulty,
            topic=topic,
            subtopic=subtopic,
            context_metadata=[
                {
                    "filename": c["metadata"].filename,
                    "page_number": c["metadata"].page_number,
                    "chunk_index": c["metadata"].chunk_index,
                }
                for c in focused_contexts
            ],
            expected_answers=expected_answers,
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

    questions = rag.generate_questions_for_topic(
        topic="Direct Methods for Optimal Control", num_subtopics=1
    )

    for q in questions:
        print(f"\nQuestion {q.question_id} (Difficulty: {q.difficulty}):")
        print(q.question)

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
