# %%
# Import required libraries
import os
from pathlib import Path

import numpy as np
from docarray import DocList
from dotenv import load_dotenv
from openai import OpenAI
from pdf_load import KnowledgeDoc, db, model
from sentence_transformers import SentenceTransformer
from vectordb import InMemoryExactNNVectorDB

# Set OpenAI API key
ROOT_DIR = Path(__file__).parent.parent
env_path = ROOT_DIR / ".env"

print(f"Current working directory: {os.getcwd()}")
print(f"Looking for .env at: {env_path}")

if not env_path.exists():
    raise FileNotFoundError(f".env file not found at {env_path}")

# Load environment variables
load_dotenv(env_path)
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


def rag_pipeline(question):
    # Step 1: Vectorize the question (prompt)
    question_embedding = model.encode(question)
    query_doc = KnowledgeDoc(text=question, embedding=question_embedding)

    # Step 2: Search in VectorDB for relevant documents
    results = db.search(inputs=DocList[KnowledgeDoc]([query_doc]), limit=3)

    # Step 3: Extract context text from the retrieved documents
    context_texts = []
    for match in results[0].matches:
        # Extract the text content of the matched documents
        context_texts.append(match.text)

    # Combine the context texts into a single string
    context_text = "\n\n".join(context_texts)

    # Step 4: Prepare the prompt with relevant context
    prompt = f"""Based on the following knowledge base content, please answer the question. Use only the provided content, and if information is insufficient, please indicate.

Knowledge Base Content:
{context_text}

Question: {question}

Please provide a clear and accurate answer, citing relevant knowledge base content. Response format:
1. Direct answer to the question
2. Citation of relevant knowledge points
3. Additional notes (if needed)"""

    # Step 5: Use OpenAI API to generate an answer with context
    messages = [
        {
            "role": "system",
            "content": "You are a professional educational assistant. Please answer questions based on the provided knowledge base content, keeping responses accurate, relevant, and well-structured.",
        },
        {"role": "user", "content": prompt},
    ]

    # Make a streaming request to OpenAI API
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini-2024-07-18",
    #     messages=messages,
    # )

    # return response.choices[0].message.content.strip()
    return messages


# Example usage
if __name__ == "__main__":
    question = (
        "What is the role of PID control in steering a car along a straight track?"
    )
    answer = rag_pipeline(question)
    print(f"Question: {question}\nAnswer: {answer}")
# %%
