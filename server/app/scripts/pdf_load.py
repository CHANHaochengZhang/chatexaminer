# %%
# Import required libraries
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

# Add server directory to Python path
SERVER_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(SERVER_DIR))

import logging
from typing import Dict, List, Optional

import fitz  # PyMuPDF
import nltk
from app.models.document import DocumentMetadata, KnowledgeDoc
from docarray import BaseDoc, DocList
from docarray.typing import NdArray
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from vectordb import InMemoryExactNNVectorDB

ROOT_DIR = Path(__file__).parent.parent.parent.parent
PDF_DIR = ROOT_DIR / "knowledge" / "pdf"

# Download required NLTK data
try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")


def clean_text(text: str) -> str:
    """Clean text"""
    # Only normalize whitespace, keep original content
    text = re.sub(r"\s+", " ", text)  # Normalize whitespace
    return text.strip()


def extract_and_chunk_pdfs(
    pdf_directory: Path = PDF_DIR,
) -> List[tuple[DocumentMetadata, str]]:
    """
    Extract text from PDFs with intelligent chunking

    Args:
        pdf_directory: Directory containing PDF files

    Returns:
        List of tuples containing metadata and text chunks
    """
    documents = []

    # Initialize text splitter with optimal parameters
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", ";", " ", ""],
    )

    pdf_directory.mkdir(parents=True, exist_ok=True)

    for filename in os.listdir(pdf_directory):
        if not filename.endswith(".pdf"):
            continue

        file_path = pdf_directory / filename
        try:
            # Process PDF using PyMuPDF (fitz)
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc):
                    # Extract text from page
                    text = page.get_text()

                    # Clean and preprocess text
                    cleaned_text = clean_text(text)
                    if not cleaned_text.strip():
                        continue

                    # langchain text chunking
                    chunks = text_splitter.split_text(cleaned_text)

                    # Process each text chunk
                    for chunk_idx, chunk in enumerate(chunks):
                        # Skip chunks that are too short
                        if len(chunk.split()) < 20:  # Minimum 20 words per chunk
                            continue

                        metadata = DocumentMetadata(
                            filename=filename,
                            page_number=page_num + 1,
                            chunk_index=chunk_idx,
                        )
                        documents.append((metadata, chunk))

        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            continue

    return documents


# Extract text from PDFs
pdf_documents = extract_and_chunk_pdfs()

# Print statistics
print(f"Total chunks extracted: {len(pdf_documents)}")
print(f"Sample chunk from first document:")
if pdf_documents:
    metadata, text = pdf_documents[0]
    print(f"File: {metadata.filename}")
    print(f"Page: {metadata.page_number}")
    print(f"Text preview: {text[:200]}...")

# %%
from sentence_transformers import SentenceTransformer

# Load pre-trained embedding model (e.g., SBERT)
model = SentenceTransformer("all-MiniLM-L6-v2")


def vectorize_documents(documents):
    """Vectorize documents with metadata"""
    vectors = []
    for metadata, text in documents:
        embedding = model.encode(text, show_progress_bar=True)
        vectors.append((metadata, text, embedding))
    return vectors


# Vectorize documents
document_vectors = vectorize_documents(pdf_documents)

# %%
# Print results
print(document_vectors)

import numpy as np

# Create vector database
db = InMemoryExactNNVectorDB[KnowledgeDoc](workspace="./vectorDB_workspace")
# %%
# Create list of all documents
doc_list = [
    KnowledgeDoc(text=text, embedding=np.array(embedding), metadata=metadata)
    for metadata, text, embedding in document_vectors
]

# Index documents into database
db.index(inputs=DocList[KnowledgeDoc](doc_list))

# %%
# Verify documents are successfully inserted into database
print(f"Number of entities in database: {len(doc_list)}")


# Modify the search function
def semantic_search(query_text: str, db, model, top_k=3):
    """Perform semantic search with metadata in results"""
    processed_query = clean_text(query_text)

    query_embedding = model.encode(processed_query)
    query_doc = KnowledgeDoc(
        text=processed_query,
        embedding=query_embedding,
        metadata=DocumentMetadata(filename="query", page_number=0, chunk_index=0),
    )

    results = db.search(inputs=DocList[KnowledgeDoc]([query_doc]), limit=top_k)
    return results


# Update your existing query code
query_text = (
    """Consider PID control applied to steer a car along a straight track. The control signal"""
)
results = semantic_search(query_text, db, model)

# Print search results with metadata
for match in results[0].matches:
    print(f"Source: {match.metadata.filename}, Page: {match.metadata.page_number}")
    print(f"Matched Text:")
    print(match.text[:1000])
    print("-" * 50)

# %%
