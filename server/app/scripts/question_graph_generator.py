import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from rag_pipeline_script import ExamQuestion, RAGPipeline


class QuestionGraphGenerator:
    def __init__(self, topics_file: Path, rag_pipeline: RAGPipeline):
        """初始化问题图生成器"""
        self.topics_file = topics_file
        self.rag = rag_pipeline

    def load_topics(self) -> List[Dict[str, str]]:
        """加载考试主题"""
        with open(self.topics_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_question_graph(self) -> Dict[str, List[ExamQuestion]]:
        """生成问题图"""
        topics = self.load_topics()[0]
        question_graph = {}

        for topic_data in topics:
            topic = topic_data["topic"]
            logging.info(f"Generating questions for topic: {topic}")

            # 为每个主题生成5个子问题
            questions_for_topic = []
            for difficulty in range(1, 6):  # 1-5难度
                try:
                    # 使用现有�� generate_question 方法
                    question = self.rag.generate_question(topic=topic, difficulty=difficulty)
                    questions_for_topic.append(question)
                    logging.info(f"Generated question with difficulty {difficulty}")
                except Exception as e:
                    logging.error(f"Error generating question for {topic}: {e}")

            question_graph[topic] = questions_for_topic

        return question_graph

    def save_questions(self, output_file: Path):
        """保存生成的问题到文件"""
        question_graph = self.generate_question_graph()

        # 转换为可序列化的格式
        serializable_graph = {
            topic: [asdict(q) for q in questions] for topic, questions in question_graph.items()
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(serializable_graph, f, indent=2, ensure_ascii=False)


def main():
    # 设置路径
    root_dir = Path(__file__).parent.parent
    topics_file = root_dir / "data" / "exam_topics.json"
    output_file = root_dir / "data" / "question_graph.json"

    # 初始化 RAG pipeline
    rag_pipeline = RAGPipeline()

    # 创建问题图生成器
    generator = QuestionGraphGenerator(topics_file, rag_pipeline)

    # 生成并保存问题
    try:
        generator.save_questions(output_file)
        logging.info(f"Successfully generated question graph and saved to {output_file}")
    except Exception as e:
        logging.error(f"Error generating question graph: {e}")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    main()
