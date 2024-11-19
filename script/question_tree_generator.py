import json
import logging
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_pipeline_script import ExamQuestion, RAGPipeline

# Configure logging
logging.basicConfig(
    filename="../data/logs/question_tree.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@dataclass
class QuestionNode:
    """Question node structure for exam question tree"""

    question: ExamQuestion
    children: List["QuestionNode"] = field(default_factory=list)
    approved: bool = False
    teacher_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for JSON serialization"""
        return {
            "question": asdict(self.question),
            "children": [child.to_dict() for child in self.children],
            "approved": self.approved,
            "teacher_notes": self.teacher_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuestionNode":
        """Create node from dictionary"""
        question = ExamQuestion(**data["question"])
        node = cls(
            question=question,
            approved=data.get("approved", False),
            teacher_notes=data.get("teacher_notes"),
        )
        node.children = [cls.from_dict(child) for child in data["children"]]
        return node


class QuestionTreeGenerator:
    def __init__(self, output_dir: Path = Path("../data/question_trees")):
        self.rag = RAGPipeline()
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_tree(
        self, topic: str, base_difficulty: int, depth: int = 2, branches: int = 3
    ) -> QuestionNode:
        """Generate a question tree for a given topic

        Args:
            topic: Main topic for questions
            base_difficulty: Initial difficulty level (1-5)
            depth: Maximum depth of the tree
            branches: Number of follow-up questions per node
        """
        logging.info(f"Generating question tree for topic: {topic}")

        # Generate root question
        root_question = self.rag.generate_question(topic, base_difficulty)
        root_node = QuestionNode(question=root_question)

        if depth > 0:
            # Generate follow-up questions
            for _ in range(branches):
                # Increase difficulty slightly for follow-ups
                child_difficulty = min(base_difficulty + 1, 5)
                child_node = self.generate_tree(
                    topic, child_difficulty, depth - 1, branches
                )
                root_node.children.append(child_node)

        return root_node

    def save_tree(self, tree: QuestionNode, filename: str):
        """Save question tree to JSON file"""
        file_path = self.output_dir / f"{filename}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(tree.to_dict(), f, indent=2, ensure_ascii=False)
        logging.info(f"Saved question tree to {file_path}")

    def load_tree(self, filename: str) -> Optional[QuestionNode]:
        """Load question tree from JSON file"""
        file_path = self.output_dir / f"{filename}.json"
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return QuestionNode.from_dict(data)


def main():
    generator = QuestionTreeGenerator()

    # Example topics and their base difficulties
    topics = [
        ("Direct methods for optimal control", 3),
        ("Indirect methods for optimal control", 4),
        # Add more topics as needed
    ]

    for topic, difficulty in topics:
        # Generate tree
        tree = generator.generate_tree(
            topic=topic,
            base_difficulty=difficulty,
            depth=5,  # Adjust depth as needed
            branches=3,  # Adjust number of branches as needed
        )

        # Save tree with sanitized filename
        filename = topic.lower().replace(" ", "_")
        generator.save_tree(tree, filename)
        logging.info(f"Generated and saved tree for topic: {topic}")


if __name__ == "__main__":
    main()
