# ChatExaminer

An intelligent examination system based on RAG (Retrieval-Augmented Generation) architecture that simulates interactive oral examinations through dynamic question generation and real-time evaluation.

## Project Overview

ChatExaminer is a proof-of-concept AI-powered oral examination system that aims to:
- Generate dynamic questions based on course materials
- Conduct interactive examinations similar to live oral exams
- Provide real-time evaluation of student responses
- Adapt questioning based on student performance
- Assist human examiners with performance assessment

## Key Features

- 🎯 Dynamic Question Generation
  - Generates questions from course materials
  - Creates adaptive dialogue trees
  - Aligns with syllabus and learning objectives

- 🤖 Interactive Examination
  - Simulates real oral exam scenarios
  - Provides follow-up questions based on responses
  - Maintains conversation context

- 📊 Automated Evaluation
  - Assesses student responses in real-time
  - Provides detailed performance metrics
  - Generates feedback for human examiners

## Technical Architecture

### Core Components

- **RAG Engine**
  - Knowledge base integration
  - Context-aware retrieval
  - Question generation

- **Dialogue Manager**
  - Conversation flow control
  - Response analysis
  - Dynamic question selection

- **Evaluation System**
  - Performance assessment
  - Feedback generation
  - Alignment verification

### Data Processing

- PDF parsing and structuring
- LaTeX representation handling
- Course material organization

## Research Focus

This project addresses the following research questions:

1. How can AI systems effectively simulate interactive oral examination dynamics?
2. How can we ensure AI-generated questions align with teacher-defined criteria?
3. What methods can effectively evaluate AI-student interactions in educational contexts?

## Development Status

Current development focuses on:
- [ ] Knowledge base integration
- [ ] Question generation algorithms
- [ ] Interactive dialogue management
- [ ] Evaluation metrics implementation
- [ ] Teacher control interface

## Getting Started

[Development setup instructions will be added as the project progresses]

### Configuration

1. Create a `.env` file and set the following environment variables:

```
OPENAI_API_KEY=<your-openai-api-key>
```

## Code Architecture

### Directory Structure
```
project_root/
├── knowledge/
│   └── pdf/            # PDF knowledge base files
├── data/               # Generated data storage
│   └── exam_questions.json  # Generated exam questions
├── script/
│   ├── pdf_load.py     # PDF processing and vectorization
│   ├── rag_pipeline_script.py  # Main RAG pipeline
│   └── rag/
│       └── core.py     # Core examination system
└── .env                # Environment configuration
```

### Core Components Overview

#### 1. PDF Processing (`pdf_load.py`)
- **Purpose**: Handles PDF document processing and vectorization
- **Key Classes**:
  - `DocumentMetadata`: Stores document chunk metadata (filename, page number, chunk index)
  - `KnowledgeDoc`: Document schema with metadata and embeddings
- **Key Functions**:
  - `extract_and_chunk_pdfs()`: Intelligent text extraction and chunking
  - `vectorize_documents()`: Generates embeddings using SentenceTransformer
  - `clean_text()`: Text preprocessing and stopwords removal
- **Features**:
  - Intelligent chunking with RecursiveCharacterTextSplitter
  - Quality control for text chunks
  - Error handling for PDF processing
  - Metadata preservation

#### 2. RAG Pipeline (`rag_pipeline_script.py`)
- **Purpose**: Implements the main RAG pipeline for question generation and evaluation
- **Key Classes**:
  - `ExamQuestion`: Structure for storing exam questions
  - `RAGPipeline`: Main pipeline controller
- **Key Features**:
  - JSON-based question storage and retrieval
  - Enhanced context relevance scoring
  - Question generation with GPT-4
  - Answer evaluation with detailed feedback
- **Integration**: Connects PDF processing with examination system

#### 3. Examination System (`rag/core.py`)
- **Purpose**: Core examination logic and context management
- **Key Classes**:
  - `ExamContext`: Manages examination session information
  - `RAGResponse`: Structures generated questions and context
  - `ExaminerRAG`: Main examination controller
- **Features**:
  - Question generation
  - Answer evaluation
  - Context-aware prompting

### Component Interactions

1. **Knowledge Base Creation**
   ```mermaid
   graph LR
   A[PDF Files] --> B[pdf_load.py]
   B --> C[Vector Database]
   ```

2. **Question Generation Flow**
   ```mermaid
   graph LR
   A[ExamContext] --> B[RAGPipeline]
   B --> C[Context Retrieval]
   C --> D[GPT-4 Generation]
   D --> E[JSON Storage]
   ```

3. **Answer Evaluation Flow**
   ```mermaid
   graph LR
   A[Student Answer] --> B[RAGPipeline]
   B --> C[Context Retrieval]
   C --> D[GPT-4 Evaluation]
   D --> E[Feedback Generation]
   ```

### Key Dependencies
- OpenAI API: For GPT-4o-mini based generation and evaluation
- SentenceTransformer: For text embedding
- Vector Database: For efficient knowledge retrieval
- PyMuPDF: For PDF processing

### Configuration
The system requires proper configuration of:
- OpenAI API key in `.env`
- Knowledge base PDFs in `knowledge/pdf/`
- Vector database workspace settings
- Data storage directory for generated questions
