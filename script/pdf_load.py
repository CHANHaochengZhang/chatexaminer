# %%
# Import required libraries
import os

import fitz  # PyMuPDF

pdf_directory = "../knowledge/pdf"  # Directory containing PDF files


def extract_text_from_pdfs(pdf_directory):
    documents = []
    for filename in os.listdir(pdf_directory):
        if filename.endswith(".pdf"):
            file_path = os.path.join(pdf_directory, filename)
            with fitz.open(file_path) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
                documents.append((filename, text))
    return documents


# Extract text from PDFs
pdf_documents = extract_text_from_pdfs(pdf_directory)


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
db = InMemoryExactNNVectorDB[KnowledgeDoc](workspace="./workspace_path")
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
 uk corresponds to the angle between the front wheel and the centerline of the track, the
 input signal xk corresponds to the angle between the car body and the track in degrees,
 and the goal of the PID controller is to bring the angle between the car body and the
 track to a value of x∗ = 4 degrees (corresponding to executing a turn). Figure 1 shows
 the behavior of both xk and uk at time steps k = 0,1,2,.... Suppose the PID controller
 takes the form described in the lecture notes, and assume Kd = Ki = 0, which one of
 the following options are true?"""
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
