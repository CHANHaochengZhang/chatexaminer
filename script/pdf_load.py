# %%
# Import required libraries
import os
import re
from typing import List

import fitz  # PyMuPDF
import nltk
from nltk.corpus import stopwords

pdf_directory = "../knowledge/pdf"  # Directory containing PDF files

# Download required NLTK data
try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")


def get_stopwords() -> set:
    """Get English stopwords"""
    return set(stopwords.words("english"))


def clean_text(text: str, stop_words: set) -> str:
    """Clean text and remove stopwords"""
    # Basic cleaning
    text = text.lower()
    text = re.sub(r"\s+", " ", text)  # Normalize whitespace
    text = re.sub(r"[^a-zA-Z\s]", " ", text)  # Keep only English letters

    # Remove stopwords
    words = text.split()
    cleaned_words = [word for word in words if word not in stop_words]

    return " ".join(cleaned_words)


def extract_and_chunk_pdfs(pdf_directory):
    """Extract text from PDFs with preprocessing"""
    stop_words = get_stopwords()
    documents = []

    for filename in os.listdir(pdf_directory):
        if filename.endswith(".pdf"):
            file_path = os.path.join(pdf_directory, filename)
            with fitz.open(file_path) as doc:
                for page in doc:
                    text = page.get_text()
                    # Clean and preprocess text
                    cleaned_text = clean_text(text, stop_words)
                    if cleaned_text.strip():  # Ensure non-empty text
                        paragraphs = cleaned_text.split("\n\n")
                        for paragraph in paragraphs:
                            if len(paragraph.split()) > 5:  # Minimum words threshold
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
    """Vectorize documents"""
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


# Modify the search function
def semantic_search(query_text: str, db, model, top_k=3):
    """Perform semantic search with preprocessed query"""
    # Preprocess query
    stop_words = get_stopwords()
    processed_query = clean_text(query_text, stop_words)

    # Generate query embedding
    query_embedding = model.encode(processed_query)
    query_doc = KnowledgeDoc(text=processed_query, embedding=query_embedding)

    # Execute search
    results = db.search(inputs=DocList[KnowledgeDoc]([query_doc]), limit=top_k)
    return results


# Update your existing query code
query_text = """Consider PID control applied to steer a car along a straight track. The control signal"""
results = semantic_search(query_text, db, model)

# Print search results
for match in results[0].matches:
    # print(f"Match score: {match}")
    print(f"Matched Document Text:")
    print(match.text[:1000])
    print("-" * 50)

# %%
