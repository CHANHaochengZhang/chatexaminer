# %%
# Import required libraries
import os
from pathlib import Path

from docarray import DocList

# Set OpenAI API key
from dotenv import load_dotenv
from openai import OpenAI
from pdf_load import KnowledgeDoc, db, model
from sentence_transformers import SentenceTransformer
from vectordb import InMemoryExactNNVectorDB

# 获取项目根目录（脚本所在目录的父目录）
ROOT_DIR = Path(__file__).parent.parent
env_path = ROOT_DIR / ".env"

print(f"Current working directory: {os.getcwd()}")
print(f"Looking for .env at: {env_path}")

if not env_path.exists():
    raise FileNotFoundError(f".env file not found at {env_path}")

# 加载环境变量
load_dotenv(env_path)
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)
# %%
# Define RAG pipeline


def rag_pipeline(question):
    # Step 1: Vectorize the question
    question_embedding = model.encode(question)
    query_doc = KnowledgeDoc(text=question, embedding=question_embedding)

    # Step 2: Search in VectorDB for relevant documents
    results = db.search(inputs=DocList[KnowledgeDoc]([query_doc]), limit=5)

    # Step 3: Format context, remove extra whitespace and special characters, and filter most relevant passages
    context_texts = []
    for match in results[0].matches:
        # Clean text: remove extra whitespace and special characters
        cleaned_text = " ".join(match.text.split())
        # Select only the most relevant parts (through simple keyword matching)
        if any(keyword in cleaned_text.lower() for keyword in question.lower().split()):
            context_texts.append(cleaned_text)

    # If no particularly relevant passages found, select the three shortest passages
    if not context_texts:
        context_texts = sorted([match.text for match in results[0].matches], key=len)[
            :3
        ]

    context_text = "\n\n".join(context_texts)

    # Step 4: Use more structured prompt
    prompt = f"""Based on the following knowledge base content, please answer the question. Use only the provided content, and if information is insufficient, please indicate.

Knowledge Base Content:
{context_text}

Question: {question}

Please provide a clear and accurate answer, citing relevant knowledge base content. Response format:
1. Direct answer to the question
2. Citation of relevant knowledge points
3. Additional notes (if needed)"""

    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {
                "role": "system",
                "content": "You are a professional educational assistant. Please answer questions based on the provided knowledge base content, keeping responses accurate, relevant, and well-structured.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=300,
    )

    return response.choices[0].message.content.strip()


# Example usage
if __name__ == "__main__":
    question = (
        "What is the role of PID control in steering a car along a straight track?"
    )
    answer = rag_pipeline(question)
    print(f"Question: {question}\nAnswer: {answer}")
# %%
