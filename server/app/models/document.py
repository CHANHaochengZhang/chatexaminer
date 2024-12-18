from dataclasses import dataclass
from typing import Optional

from docarray import BaseDoc
from docarray.typing import NdArray


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
    embedding: NdArray[384]  # 使用 sentence-transformers 的默认维度
    metadata: DocumentMetadata
