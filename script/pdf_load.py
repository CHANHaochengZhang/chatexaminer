# %%
# Import required libraries
import os
import re
from dataclasses import dataclass

import fitz  # PyMuPDF
import nltk
from docarray import BaseDoc, DocList
from docarray.typing import NdArray
from nltk.corpus import stopwords
from vectordb import InMemoryExactNNVectorDB

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


@dataclass
class DocumentMetadata:
    """Metadata for document chunks"""

    filename: str
    page_number: int
    chunk_index: int
    # difficulty_level: Optional[int] = None


class KnowledgeDoc(BaseDoc):
    """Document schema with metadata"""

    text: str
    embedding: NdArray[384]
    metadata: DocumentMetadata


def extract_and_chunk_pdfs(pdf_directory):
    """Extract text from PDFs with metadata"""
    stop_words = get_stopwords()
    documents = []

    for filename in os.listdir(pdf_directory):
        if filename.endswith(".pdf"):
            file_path = os.path.join(pdf_directory, filename)
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    cleaned_text = clean_text(text, stop_words)
                    if cleaned_text.strip():
                        paragraphs = cleaned_text.split("\n\n")
                        for chunk_idx, paragraph in enumerate(paragraphs):
                            if len(paragraph.split()) > 5:
                                metadata = DocumentMetadata(
                                    filename=filename,
                                    page_number=page_num + 1,
                                    chunk_index=chunk_idx,
                                )
                                documents.append((metadata, paragraph))
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
    stop_words = get_stopwords()
    processed_query = clean_text(query_text, stop_words)

    query_embedding = model.encode(processed_query)
    query_doc = KnowledgeDoc(
        text=processed_query,
        embedding=query_embedding,
        metadata=DocumentMetadata(filename="query", page_number=0, chunk_index=0),
    )

    results = db.search(inputs=DocList[KnowledgeDoc]([query_doc]), limit=top_k)
    return results


# Update your existing query code
query_text = """Consider PID control applied to steer a car along a straight track. The control signal"""
results = semantic_search(query_text, db, model)

# Print search results with metadata
for match in results[0].matches:
    print(f"Source: {match.metadata.filename}, Page: {match.metadata.page_number}")
    print(f"Matched Text:")
    print(match.text[:1000])
    print("-" * 50)

# %%
