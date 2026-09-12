from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from uuid import uuid4

from rag.chunker import chunk_document
from rag.document_parser import parse_document
from rag.embeddings import EmbeddingService
from rag.vector_store import VectorStore


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".md",
}


class IngestionService:
    """
    文档入库服务。

    负责：
    File
      ↓
    Parser
      ↓
    Chunker
      ↓
    Embedding
      ↓
    VectorStore
    """

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.embedding_service = (
            embedding_service
            or EmbeddingService()
        )

        self.vector_store = (
            vector_store
            or VectorStore()
        )

    def ingest(
        self,
        file_path: str | Path,
        document_id: str | None = None,
        original_file_name: str | None = None,
    ) -> dict:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"文件不存在：{file_path}"
            )

        suffix = file_path.suffix.lower()

        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"暂不支持该文件类型：{suffix}"
            )

        document_id = (
            document_id
            or uuid4().hex
        )

        uploaded_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        document = parse_document(
            file_path
        )
        if original_file_name:
            document["file_name"] = (
                original_file_name
            )

        chunks = chunk_document(
            document
        )

        if not chunks:
            raise ValueError(
                "文档中没有可用于检索的文本内容"
            )

        texts = [
            chunk["text"]
            for chunk in chunks
        ]

        embeddings = (
            self.embedding_service
            .embed_texts(texts)
        )

        self.vector_store.upsert_chunks(
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
            uploaded_at=uploaded_at,
        )

        return {
            "document_id": document_id,
            "file_name": document[
                "file_name"
            ],
            "file_type": document[
                "file_type"
            ],
            "uploaded_at": uploaded_at,
            "chunk_count": len(chunks),
            "embedding_dimension": (
                len(embeddings[0])
                if embeddings
                else 0
            ),
        }
