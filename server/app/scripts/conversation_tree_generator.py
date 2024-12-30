# %%
import json
import logging
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_pipeline_script import ExamQuestion, RAGPipeline

# Configure logging
logging.basicConfig(
    filename="../data/logs/conversation_tree.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@dataclass
class ConversationNode:
    """Conversation node structure for exam conversation tree"""

    question: ExamQuestion
    children: List["ConversationNode"] = field(default_factory=list)
    approved: bool = False
    teacher_notes: Optional[str] = None
    context: List[str] = field(default_factory=list)
    difficulty: int = 1
    topic: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    answer_examples: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for JSON serialization"""
        return {
            "question": asdict(self.question),
            "children": [child.to_dict() for child in self.children],
            "approved": self.approved,
            "teacher_notes": self.teacher_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationNode":
        """Create node from dictionary"""
        question = ExamQuestion(**data["question"])
        node = cls(
            question=question,
            approved=data.get("approved", False),
            teacher_notes=data.get("teacher_notes"),
        )
        node.children = [cls.from_dict(child) for child in data["children"]]
        return node


class ConversationTreeGenerator:
    def __init__(self):
        self.rag = RAGPipeline()
        self.response_types = ["correct", "partial", "incorrect"]
        self.output_dir = Path("../data/conversation_trees")
        self.output_dir.mkdir(exist_ok=True)

    def _generate_base_question(
        self, topic: str, difficulty: int, context_text: str = None
    ) -> ExamQuestion:
        """Generate base question using RAG Pipeline"""
        question = self.rag.generate_question(
            topic=topic,
            difficulty=difficulty,
        )

        if context_text:
            question.context.append(context_text)

        return question

    def _generate_answer_examples(self, question: ExamQuestion) -> Dict[str, List[str]]:
        """Generate a range of example answers for the question"""
        example_answers = {
            "excellent": "An excellent answer that demonstrates deep understanding...",
            "good": "A good answer that covers the main points...",
            "basic": "A basic answer that shows minimal understanding...",
            "poor": "An incomplete or incorrect answer...",
        }

        evaluations = {}
        for level, answer in example_answers.items():
            evaluation = self.rag.answer_question(question.question_id, answer)
            evaluations[level] = [answer, evaluation]

        return evaluations

    def _adjust_difficulty(self, current_difficulty: int, response_type: str) -> int:
        """Adjust question difficulty based on student response type"""
        adjustments = {
            "correct": 1,  # Correct answer: increase difficulty
            "partial": 0,  # Partially correct: maintain difficulty
            "incorrect": -1,  # Incorrect answer: decrease difficulty
        }

        # Ensure difficulty is within the range of 1-5
        new_difficulty = current_difficulty + adjustments[response_type]
        return max(1, min(5, new_difficulty))

    def generate_tree(
        self, topic: str, base_difficulty: int, depth: int = 3, context_text: str = None
    ) -> ConversationNode:
        """Generate conversation tree"""
        logging.info(f"Generating conversation tree for topic: {topic}")

        root_question = self._generate_base_question(
            topic=topic, difficulty=base_difficulty, context_text=context_text
        )

        root_node = ConversationNode(
            question=root_question,
            context=root_question.context,
            difficulty=base_difficulty,
            topic=topic,
            metadata={
                "question_id": root_question.question_id,
                "context_metadata": root_question.context_metadata,
            },
        )

        root_node.answer_examples = self._generate_answer_examples(root_question)

        if depth > 0:
            for response_type in self.response_types:
                next_difficulty = self._adjust_difficulty(
                    base_difficulty, response_type
                )

                subtopic = self._generate_subtopic(topic, response_type)

                child_node = self.generate_tree(
                    topic=subtopic,
                    base_difficulty=next_difficulty,
                    depth=depth - 1,
                    context_text=context_text,
                )
                root_node.children.append(child_node)

        return root_node

    def _generate_subtopic(self, topic: str, response_type: str) -> str:
        """Generate subtopic based on response type"""
        if response_type == "correct":
            return f"{topic} - Advanced Concepts"
        elif response_type == "partial":
            return f"{topic} - Fundamentals"
        else:
            return f"{topic} - Basic Principles"

    def save_tree(self, tree: ConversationNode, filename: str):
        """Save conversation tree to JSON file"""
        file_path = self.output_dir / f"{filename}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(tree.to_dict(), f, indent=2, ensure_ascii=False)
        logging.info(f"Saved conversation tree to {file_path}")

    def load_tree(self, filename: str) -> Optional[ConversationNode]:
        """Load conversation tree from JSON file"""
        file_path = self.output_dir / f"{filename}.json"
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ConversationNode.from_dict(data)


# %%
def main():
    generator = ConversationTreeGenerator()

    topics = [
        ("Direct methods for optimal control", 3),
        ("Indirect methods for optimal control", 4),
    ]

    for topic, difficulty in topics:
        tree = generator.generate_tree(
            topic=topic,
            base_difficulty=difficulty,
            depth=2,
        )

        filename = topic.lower().replace(" ", "_")
        generator.save_tree(tree, filename)
        logging.info(f"Generated and saved tree for topic: {topic}")


if __name__ == "__main__":
    main()
# %%
