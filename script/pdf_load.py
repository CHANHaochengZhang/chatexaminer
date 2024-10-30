# %%
# Import required libraries
import os

import fitz  # PyMuPDF

pdf_directory = "../knowledge/pdf"  # Directory containing PDF files


def extract_and_chunk_pdfs(pdf_directory):
    documents = []
    for filename in os.listdir(pdf_directory):
        if filename.endswith(".pdf"):
            file_path = os.path.join(pdf_directory, filename)
            with fitz.open(file_path) as doc:
                for page in doc:
                    text = page.get_text()
                    paragraphs = text.split("\n\n")
                    for paragraph in paragraphs:
                        documents.append((filename, paragraph))
    return documents


# Extract text from PDFs
pdf_documents = extract_and_chunk_pdfs(pdf_directory)


# Print results
print(pdf_documents)

# %%
from sentence_transformers import SentenceTransformer

# Load pre-trained embedding model (e.g., SBERT)
model = SentenceTransformer("all-MiniLM-L6-v2")


def vectorize_documents(documents):
    vectors = []
    for filename, text in documents:
        embedding = model.encode(text, show_progress_bar=True)
        vectors.append((filename, text, embedding))
    return vectors


# Vectorize documents
document_vectors = vectorize_documents(pdf_documents)

# %%
# Print results
print(document_vectors)

import numpy as np

# %%
from docarray import BaseDoc, DocList
from docarray.typing import NdArray
from vectordb import InMemoryExactNNVectorDB


# Define document schema
class KnowledgeDoc(BaseDoc):
    text: str
    embedding: NdArray[384]  # Dimension of SBERT embeddings


# Create vector database
db = InMemoryExactNNVectorDB[KnowledgeDoc](workspace="./vectorDB_workspace")
# %%
# Create list of all documents
doc_list = [
    KnowledgeDoc(text=text, embedding=np.array(embedding))
    for filename, text, embedding in document_vectors
]

# Index documents into database
db.index(inputs=DocList[KnowledgeDoc](doc_list))

# %%
# Verify documents are successfully inserted into database
print(f"Number of entities in database: {len(doc_list)}")

# Perform simple retrieval test
query_text = """ Consider PID control applied to steer a car along a straight track. The control signal
"""
query_embedding = model.encode(query_text)
query_doc = KnowledgeDoc(text=query_text, embedding=query_embedding)

# Execute search
results = db.search(inputs=DocList[KnowledgeDoc]([query_doc]), limit=3)
# Print search results
for match in results[0].matches:
    print(f"Matched Document Text:")
    print(match.text[:1000])
    print("-" * 50)

# %%
