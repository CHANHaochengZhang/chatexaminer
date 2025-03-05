# ChatExaminer中的RAG实现

## 简介

检索增强生成（Retrieval Augmented Generation，简称RAG）是ChatExaminer系统的核心技术之一，它通过将信息检索与生成模型相结合，显著提高了系统在口试评估中的质量、准确性和领域相关性。本文档详细介绍RAG技术在ChatExaminer中的实现原理、关键组件和应用场景。

## RAG基本原理

RAG系统的基本工作原理是：
1. **检索（Retrieval）**：根据输入查询从知识库中检索相关文档或信息片段
2. **增强（Augmentation）**：将检索到的信息与原始查询结合
3. **生成（Generation）**：利用大语言模型基于增强后的输入生成高质量、知识丰富的回答

这种方法解决了大语言模型的几个关键限制：
- 减轻了"幻觉"问题，提高了回答的准确性
- 使系统能够访问最新或专业的领域知识
- 提供了可追溯的信息来源，增强了可解释性

### RAG流程图示

```mermaid
flowchart TD
    A[输入查询] --> B[向量化查询]
    B --> C[向量数据库检索]
    D[课程PDF文档] --> E[预处理]
    E --> F[文档向量化]
    F --> G[存储到向量数据库]
    G --> C
    C --> H[获取相关文档]
    H --> I[相关性评分与排序]
    I --> J[选择最佳文档]
    A --> K[构建增强提示]
    J --> K
    K --> L[大语言模型]
    L --> M[生成回答/评估]

    subgraph 预处理阶段
    D --> E --> F --> G
    end

    subgraph 检索阶段
    A --> B --> C --> H --> I --> J
    end

    subgraph 生成阶段
    K --> L --> M
    end
```

## 知识库构建详解

### 1. PDF文档处理与分块

系统从PDF课程材料中提取文本，并进行智能分块以构建知识库：

```python
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
```

分块策略特点：
1. **固定大小的块**：每块约1000字符，确保语义单元的完整性
2. **块间重叠**：相邻块重叠200字符，避免关键信息被分割
3. **自然边界分割**：优先在段落、句子等自然边界处分割文本
4. **最小内容保证**：过滤少于20个词的短块，确保内容丰富性
5. **元数据跟踪**：每个块都附带文件名、页码和块索引，便于溯源

### 2. 文档向量化

系统使用预训练的Sentence Transformer模型将文本转换为向量表示：

```python
def vectorize_documents(documents):
    """Vectorize documents with metadata"""
    vectors = []
    for metadata, text in documents:
        embedding = model.encode(text, show_progress_bar=True)
        vectors.append((metadata, text, embedding))
    return vectors

# Load pre-trained embedding model (e.g., SBERT)
model = SentenceTransformer("all-MiniLM-L6-v2")

# Vectorize documents
document_vectors = vectorize_documents(pdf_documents)

# Create vector database
db = InMemoryExactNNVectorDB[KnowledgeDoc](workspace="./vectorDB_workspace")

# Create list of all documents
doc_list = [
    KnowledgeDoc(text=text, embedding=np.array(embedding), metadata=metadata)
    for metadata, text, embedding in document_vectors
]

# Index documents into database
db.index(inputs=DocList[KnowledgeDoc](doc_list))
```

向量化过程特点：
1. **高效语义嵌入**：使用all-MiniLM-L6-v2模型，它平衡了性能和计算效率
2. **元数据保留**：在向量化过程中保留文档的元数据信息
3. **内存向量数据库**：使用InMemoryExactNNVectorDB存储向量，支持高效的最近邻搜索
4. **结构化存储**：使用KnowledgeDoc结构体统一存储文本、向量和元数据

### 3. 语义搜索实现

系统提供了语义搜索功能，用于检索与查询语义相关的文档：

```python
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
```

搜索特点：
1. **查询向量化**：将查询文本转换为与文档相同空间的向量表示
2. **语义匹配**：基于向量相似度而非关键词匹配进行检索
3. **灵活的结果数量**：可自定义返回的top_k结果数量
4. **元数据关联**：检索结果包含完整的元数据，便于溯源和后续处理

## ChatExaminer中的RAG架构

### 1. 核心组件

ChatExaminer的RAG系统由以下核心组件组成：

#### RAGPipeline类

`RAGPipeline`是整个RAG系统的核心实现，负责协调检索和生成过程：

```python
class RAGPipeline:
    def __init__(self, questions_file: Path = QUESTIONS_FILE):
        """初始化RAG管道与指定问题文件路径"""
        self.questions_file = questions_file
        self.questions = self.load_questions()

    # 其他方法...
```

#### RAGService服务

`RAGService`作为系统服务层的一部分，为前端和其他服务提供RAG功能的接口：

```python
class RAGService:
    def __init__(self):
        self.rag_pipeline = RAGPipeline(questions_file=settings.DATA_DIR / "exam_questions.json")
        self.tree_generator = ConversationTreeGenerator()

    async def generate_question(self, topic: str, difficulty: int):
        return self.rag_pipeline.generate_question(topic, difficulty)

    async def evaluate_answer(self, question_id: str, answer: str):
        return self.rag_pipeline.answer_question(question_id, answer)
```

#### 向量数据库

系统使用向量数据库存储文档嵌入，支持高效的相似性搜索：
- 使用`docarray`组织和存储文档向量
- 使用`vectordb`管理和查询这些向量

### 2. 关键流程

#### 上下文检索流程

RAG系统实现了两阶段检索策略以获取最相关的内容：

```python
def get_relevant_context(self, question: str, top_k: int = 5) -> List[str]:
    """改进的上下文检索"""
    # 将问题向量化
    question_embedding = model.encode(question)

    # 创建带元数据的查询文档
    query_doc = KnowledgeDoc(
        text=question,
        embedding=question_embedding,
        metadata=DocumentMetadata(filename="query", page_number=0, chunk_index=0),
    )

    # 在向量数据库中搜索
    results = db.search(
        inputs=DocList[KnowledgeDoc]([query_doc]),
        limit=top_k * 2,  # 初始获取更多结果以便更好的过滤
    )

    # 增强相关性评分
    scored_contexts = []
    question_keywords = set(question.lower().split())

    for match in results[0].matches:
        text = " ".join(match.text.split())  # 清理文本
        # 计算相关性分数
        text_keywords = set(text.lower().split())
        keyword_overlap = len(question_keywords & text_keywords)
        relevance_score = keyword_overlap / len(question_keywords)

        scored_contexts.append(
            {"text": text, "score": relevance_score, "metadata": match.metadata}
        )

    # 按相关性排序并选择top_k
    scored_contexts.sort(key=lambda x: x["score"], reverse=True)
    return scored_contexts[:top_k]
```

#### 问题生成流程

系统利用RAG生成考试问题，确保问题基于课程材料并具有适当的难度：

```python
def generate_question(
    self, topic: str, subtopic: str, difficulty: int, context: Dict[str, Any]
) -> ExamQuestion:
    """基于主题、子主题、难度和上下文生成问题"""
    # 实现详情...
```

### ChatExaminer中的RAG应用场景

```mermaid
graph TD
    subgraph "知识库构建"
        A1[PDF课程材料] --> A2[文档处理与分块]
        A2 --> A3[向量嵌入生成]
        A3 --> A4[存储到向量数据库]
    end

    subgraph "问题生成流程"
        B1[考试主题选择] --> B2[主题向量化]
        B2 --> B3[广泛上下文检索]
        B3 --> B4[聚焦检索]
        B4 --> B5[构建提示]
        B5 --> B6[LLM生成问题]
        B6 --> B7[结构化问题输出]
    end

    subgraph "回答评估流程"
        C1[学生回答] --> C2[获取问题上下文]
        C2 --> C3[检索相关参考文档]
        C3 --> C4[构建评估提示]
        C4 --> C5[LLM评估回答]
        C5 --> C6[生成评分和反馈]
    end

    subgraph "状态机集成"
        D1[状态机控制对话] --> D2{需要生成问题?}
        D2 -- 是 --> B1
        D2 -- 否 --> D3{需要评估回答?}
        D3 -- 是 --> C1
        D3 -- 否 --> D4[继续对话流程]
        B7 --> D5[更新状态机状态]
        C6 --> D5
    end

    A4 -.-> B3
    A4 -.-> C3
```

## RAG在问题生成中的实现细节

### 1. 问题生成流程详解

问题生成是ChatExaminer中RAG技术的核心应用，它通过多阶段处理实现高质量、与课程内容紧密对齐的考试问题：

```mermaid
flowchart TD
    A[选择考试主题] --> B[广泛主题检索]
    B --> C[选择子主题]
    C --> D[聚焦内容检索]
    D --> E[生成问题提示]
    E --> F[LLM生成问题]
    F --> G[生成参考答案]
    G --> H[存储问题与答案]

    subgraph 主题选择阶段
    A --> B --> C
    end

    subgraph 内容增强阶段
    C --> D
    end

    subgraph 问题生成阶段
    D --> E --> F --> G --> H
    end
```

#### 步骤1: 广泛主题检索

首先，系统基于用户选择的主题进行广泛的知识库检索，为后续提问奠定知识基础：

```python
def get_broad_context(self, topic: str, top_k: int = 15) -> List[Dict[str, Any]]:
    """First-round search: Get broad context related to the topic"""
    # Vectorize the topic
    topic_embedding = model.encode(topic)
    query_doc = KnowledgeDoc(
        text=topic,
        embedding=topic_embedding,
        metadata=DocumentMetadata(filename="query", page_number=0, chunk_index=0),
    )

    # Perform vector search
    results = db.search(
        inputs=DocList[KnowledgeDoc]([query_doc]),
        limit=top_k,
    )

    # Extract result texts and metadata
    broad_contexts = [
        {"text": match.text, "metadata": match.metadata} for match in results[0].matches
    ]

    # Filter to ensure contexts are sufficiently different
    filtered_contexts = []
    used_texts = set()

    for context in broad_contexts:
        # Use first 100 characters as a unique identifier
        text_key = context["text"][:100]
        if text_key not in used_texts:
            used_texts.add(text_key)
            filtered_contexts.append(context)
            # Stop when we have enough subtopics
            if len(filtered_contexts) >= num_subtopics:
                break

    return filtered_contexts
```

#### 步骤2: 聚焦内容检索

针对选定的子主题，系统进行更精确的检索，获取连续、相关的内容：

```python
def focused_search(self, selected_context: Dict[str, Any], top_k: int = 3) -> List[Dict[str, Any]]:
    """Second-round search: Focused search based on selected content ensuring continuity"""
    # Vectorize the selected context
    context_embedding = model.encode(selected_context["text"])
    query_doc = KnowledgeDoc(
        text=selected_context["text"],
        embedding=context_embedding,
        metadata=DocumentMetadata(filename="query", page_number=0, chunk_index=0),
    )

    # Get initial results
    results = db.search(
        inputs=DocList[KnowledgeDoc]([query_doc]),
        limit=top_k * 2,  # Get more initial results to find continuous blocks
    )

    # Group contexts by file and page
    grouped_contexts = {}
    for match in results[0].matches:
        key = (match.metadata.filename, match.metadata.page_number)
        if key not in grouped_contexts:
            grouped_contexts[key] = []
        grouped_contexts[key].append(
            {
                "text": match.text,
                "metadata": match.metadata,
                "chunk_index": match.metadata.chunk_index,
            }
        )

    # Find continuous blocks
    continuous_contexts = []
    for contexts in grouped_contexts.values():
        # Sort by chunk index
        contexts.sort(key=lambda x: x["chunk_index"])

        # Find continuous sequences
        current_sequence = []
        for context in contexts:
            if not current_sequence:
                current_sequence.append(context)
            elif context["chunk_index"] == current_sequence[-1]["chunk_index"] + 1:
                current_sequence.append(context)
            # When sequence breaks, store existing sequence and start new one
            else:
                if len(current_sequence) > 1:  # Only keep sequences of length > 1
                    continuous_contexts.append(current_sequence)
                current_sequence = [context]

    # Choose longest continuous sequence
    if continuous_contexts:
        longest_sequence = max(continuous_contexts, key=len)
        return longest_sequence[:top_k]  # Limit returned amount

    # If no continuous sequences, return original results
    return [
        {"text": match.text, "metadata": match.metadata}
        for match in results[0].matches[:top_k]
    ]
```

#### 步骤3: 问题生成

基于检索到的内容，系统构建专用提示并调用LLM生成考试问题：

```python
def generate_question(
    self, topic: str, subtopic: str, difficulty: int, context: Dict[str, Any]
) -> ExamQuestion:
    """Generate a single question"""
    # Get existing questions for the same subtopic and different difficulty
    existing_questions = [
        q
        for q in self.questions.values()
        if q.subtopic == subtopic and q.difficulty != difficulty
    ]

    # Build prompt for existing questions
    existing_questions_prompt = ""
    if existing_questions:
        existing_questions_prompt = "\nExisting questions for this subtopic:\n"
        for q in existing_questions:
            existing_questions_prompt += f"- Difficulty {q.difficulty}/5: {q.question}\n"

    # Add filename and page number information
    source_info = f"Source: {context['metadata'].filename}, Page {context['metadata'].page_number}"

    # Retrieve focused contexts
    focused_contexts = self.focused_search(context)
    context_text = "\n".join(c["text"] for c in focused_contexts)

    # Enhanced prompt for specific question generation
    prompt = f"""Based on the following specific context, generate a precise and focused exam question related to the topic '{topic}'.

Topic: {topic}
Difficulty: {difficulty}/5
Selected Content: {context['text'][:200]}...

{existing_questions_prompt}
Requirements:
1. Focus on a single, specific concept, formula, or relationship related to the topic
2. Question must be answerable using ONLY the provided context
3. Maximum length: 15 words
4. Question difficulty should be distinct from existing questions:
   - Difficulty 1: Basic recall and simple understanding
   - Difficulty 2: Application of concepts
   - Difficulty 3: Analysis and relationships
   - Difficulty 4: Evaluation and comparison
   - Difficulty 5: Synthesis and deep understanding
5. Instead of asking "What is X?", consider:
   - Difficulty 1-2: Components, parameters, basic relationships
   - Difficulty 3: Mathematical meanings, specific conditions
   - Difficulty 4: Compare and contrast, advantages/disadvantages
   - Difficulty 5: Complex relationships, theoretical implications

Context for reference:
{context_text}

Generate a focused question that tests understanding at the appropriate difficulty level."""

    # Generate question using GPT-4
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {
                "role": "system",
                "content": "You are an expert at generating precise, focused exam questions. Avoid broad, open-ended questions."
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
    )

    question_text = response.choices[0].message.content.strip()

    # Generate reference answers... (omitted)

    # Create question object and save
    question = ExamQuestion(
        question_id=f"Q{len(self.questions) + 1}",
        question=question_text,
        context=[c["text"] for c in focused_contexts],
        difficulty=difficulty,
        topic=topic,
        subtopic=subtopic,
        context_metadata=[
            {
                "filename": c["metadata"].filename,
                "page_number": c["metadata"].page_number,
                "chunk_index": c["metadata"].chunk_index,
            }
            for c in focused_contexts
        ],
        expected_answers=expected_answers,  # Contains reference answers
    )

    self.questions[question.question_id] = question
    self.save_questions()

    return question
```

### 2. 问题生成的创新特点

ChatExaminer的RAG增强问题生成具有以下创新特点：

#### 多难度分层生成

系统能根据指定难度生成不同层次的问题，并在提示中明确定义难度级别：
- **难度1**：基本概念回忆与简单理解
- **难度2**：概念应用和基本解释
- **难度3**：概念间关系分析和条件应用
- **难度4**：不同概念的评估与比较
- **难度5**：综合应用和深度理解

#### 课程内容对齐保证

系统通过多层检索策略确保问题紧密对齐课程内容：
1. 广泛主题检索：确定相关文档
2. 子主题选择：确保覆盖主题的不同方面
3. 聚焦内容检索：获取连续、详细的内容块
4. 上下文融合提示：确保问题基于实际教材生成

#### 问题差异化保证

系统采用多种策略确保生成的问题具有差异性：
1. 记录已生成问题，避免重复
2. 在提示中包含已有问题作为参考
3. 对文本片段进行多样化筛选
4. 通过文本特征提取引导不同问题形式

#### 参考答案生成

系统不仅生成问题，还通过RAG生成多级参考答案，用于后续评估：
1. **正确答案**：包含所有关键点的完整回答
2. **部分正确**：包含一些正确点但缺少关键细节的回答
3. **错误答案**：展示常见误解的回答

#### 可溯源性设计

每个生成的问题都保留完整的溯源信息：
1. 来源文档名称
2. 页码和块索引
3. 使用的完整上下文
4. 问题生成提示

这种设计使教师能够追踪问题的来源，确保质量和准确性。

## RAG在系统中的应用

### 1. 考试问题生成

RAG技术用于生成与课程材料紧密对齐的问题：
1. 首先在向量数据库中检索与主题相关的广泛上下文
2. 进行聚焦搜索获取连续的文本块
3. 基于检索到的内容构建提示
4. 使用LLM生成包含问题、正确答案和评分标准的结构化输出

### 2. 学生回答评估

RAG在评估学生回答时发挥关键作用：

```python
def evaluate_answer(
    self, question: str, answer: str, exam_context: ExamContext
) -> Dict[str, Any]:
    """评估学生的回答"""
    # 检索用于评估的相关文档
    docs = self._retrieve_relevant_docs(
        exam_context.current_topic, exam_context
    )

    # 创建评估提示
    eval_prompt = self._create_evaluation_prompt(
        question, answer, docs, exam_context
    )

    # 评估逻辑...
```

评估提示结合了检索到的相关文档，使评估更加准确：

```python
def _create_evaluation_prompt(
    self,
    question: str,
    student_answer: str,
    relevant_docs: List[str],
    exam_context: ExamContext,
) -> str:
    """创建评估提示"""
    prompt = (
        "Please evaluate the student's answer:\n\n"
        f"Question: {question}\n\n"
        f"Student's Answer: {student_answer}\n\n"
        f"Reference Knowledge:\n{chr(10).join(relevant_docs)}\n\n"
        "Evaluation Requirements:\n"
        "1. Accuracy: Does the answer align with knowledge base content\n"
        "2. Completeness: Does it cover all aspects of the question\n"
        "3. Depth of Understanding: Does it demonstrate deep concept comprehension\n"
        "4. Clarity: Is the answer well-structured and clear\n\n"
        "Please provide:\n"
        "1. Score (0-100)\n"
        "2. Detailed evaluation\n"
        "3. Suggestions for improvement"
    )
    return prompt
```

### 3. 与状态机集成

RAG系统与状态机紧密集成，支持智能对话流程：

```
状态机和RAG系统的协作流程如下：
1. 状态机接收用户输入并确定当前状态
2. 基于当前状态和输入确定下一个状态
3. 如需生成问题，调用RAG系统的`generate_question`方法
4. RAG系统基于话题从知识库检索相关文档
5. RAG系统使用检索到的文档生成问题
6. 状态机将问题展示给学生
7. 学生回答后，状态机再次分析状态并可能调用RAG的`evaluate_answer`方法
```

## 技术特点与优势

### 1. 两阶段检索策略

ChatExaminer实现了创新的两阶段检索策略：
- **广泛检索**：首先获取与主题广泛相关的文档
- **聚焦检索**：然后基于初步结果进行更精确的检索，确保获取连续、相关的信息

### 2. 增强的相关性评分

系统使用关键词重叠和语义相似性相结合的方法计算相关性：
- 从向量相似性获取初步结果
- 通过关键词重叠计算额外的相关性分数
- 组合两种方法确保检索质量

### 3. 文档连续性保证

系统特别关注检索文档的连续性，确保生成的问题和评估基于完整的上下文：
- 通过元数据跟踪文档块的连续性
- 优先选择来自同一文档且连续的文本块
- 减少了因碎片化信息导致的误解

## 结论

RAG技术是ChatExaminer系统的关键创新点，通过将检索与生成相结合，实现了：
1. 高质量、与课程材料紧密对齐的问题生成
2. 基于实际知识的准确评估
3. 智能化的对话管理

这种实现不仅提高了系统的准确性和可靠性，也为口试过程中的知识评估提供了坚实的技术基础。通过RAG技术，ChatExaminer能够模拟真实考官的行为，提供基于实际课程内容的评估和反馈。

## 在论文中讨论RAG

在论文中讨论RAG技术时，可以从以下几个方面展开：

### 1. RAG解决的核心问题

重点强调RAG如何解决大语言模型在教育评估中面临的"幻觉"问题：
- 通过检索实际课程材料确保问题和评估的准确性
- 减少生成与课程不相关内容的可能性
- 提供基于事实的评估依据

### 2. 技术创新点

描述ChatExaminer在RAG实现上的创新：
- 两阶段检索策略（广泛检索+聚焦检索）
- 连续文本块获取机制，确保上下文完整性
- 混合相关性评分（向量相似度+关键词重叠）

### 3. 实验验证

展示RAG技术在实际应用中的效果：
- 与非RAG版本的评估质量对比
- 问题相关性和评估准确性的用户研究
- 系统性能指标（检索速度、准确率等）

### 4. 与现有工作比较

将ChatExaminer的RAG实现与现有研究进行比较：
- 传统RAG模型与教育场景优化RAG的区别
- 相比其他口试系统的优势
- 在特定领域知识评估中的优化方向

## 未来工作

虽然当前的RAG实现已经能够有效支持ChatExaminer的核心功能，但仍有以下几个方向可以进一步优化：

### 1. 检索增强技术提升

- **混合检索方法**：结合关键词检索和语义检索，进一步提高相关文档的检索质量
- **动态上下文窗口**：根据问题复杂度自适应调整检索文档数量
- **跨文档推理**：实现从多个文档中整合信息，支持更复杂的知识合成

### 2. 评估增强

- **对比评估**：将学生回答与多个参考答案进行对比，提供更全面的评估
- **错误分析**：识别学生回答中的具体错误概念并提供针对性反馈
- **进度跟踪**：基于学生在不同主题的表现动态调整问题难度

### 3. 知识库优化

- **增量更新**：实现知识库的增量更新机制，无需重建整个向量数据库
- **多模态支持**：扩展到图像、图表等多模态内容，支持更丰富的教学材料
- **层次化索引**：构建主题-子主题层次结构，提高检索精确度

### 4. 性能优化

- **检索缓存**：缓存常见查询结果，减少重复计算
- **模型量化**：对嵌入模型进行量化，减少内存占用
- **分布式索引**：支持更大规模知识库的分布式检索

通过这些优化，ChatExaminer的RAG系统将能够更好地支持个性化、准确和高效的口试评估场景，为教育技术领域提供有价值的参考实现。
