from pathlib import Path

import chromadb


DEFAULT_COLLECTION_NAME = "rag_documents"

DEFAULT_PERSIST_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "chroma"
)


class VectorStore:
    """
    Chroma 向量存储服务。

    负责：
    1. 持久化 document chunks
    2. 保存 chunk metadata
    3. 根据 query embedding 执行 Top-K 检索
    """

    def __init__(
        self,
        persist_dir: str | Path = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ):
        self.persist_dir = Path(persist_dir)

        self.persist_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir)
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": "cosine"
                }
            )
        )

    def upsert_chunks(
        self,
        document_id: str,
        chunks: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """
        将文档 chunks 及其 embeddings 写入 Chroma。
        """

        if not document_id.strip():
            raise ValueError(
                "document_id 不能为空"
            )

        if len(chunks) != len(embeddings):
            raise ValueError(
                "chunks 和 embeddings 数量必须一致"
            )

        if not chunks:
            return

        ids = []
        documents = []
        metadatas = []

        for chunk, embedding in zip(
            chunks,
            embeddings
        ):
            chunk_index = chunk[
                "chunk_index"
            ]

            ids.append(
                f"{document_id}:{chunk_index}"
            )

            documents.append(
                chunk["text"]
            )

            metadata = {
                "document_id": document_id,
                "file_name": chunk[
                    "file_name"
                ],
                "file_type": chunk[
                    "file_type"
                ],
                "chunk_index": chunk_index,
                "section_index": chunk[
                    "section_index"
                ],
                "start_char": chunk[
                    "start_char"
                ],
                "end_char": chunk[
                    "end_char"
                ],
            }

            page = chunk.get("page")

            if page is not None:
                metadata["page"] = page

            metadatas.append(metadata)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[dict]:
        """
        使用 query embedding 执行 Top-K 检索。
        """

        if not query_embedding:
            raise ValueError(
                "query_embedding 不能为空"
            )

        where = None

        if document_id:
            where = {
                "document_id": document_id
            }

        result = self.collection.query(
            query_embeddings=[
                query_embedding
            ],
            n_results=top_k,
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        documents = (
            result["documents"][0]
            if result["documents"]
            else []
        )

        metadatas = (
            result["metadatas"][0]
            if result["metadatas"]
            else []
        )

        distances = (
            result["distances"][0]
            if result["distances"]
            else []
        )

        results = []

        for rank, (
            document,
            metadata,
            distance,
        ) in enumerate(
            zip(
                documents,
                metadatas,
                distances,
            ),
            start=1,
        ):
            results.append(
                {
                    "rank": rank,
                    "text": document,
                    "metadata": metadata,
                    "distance": distance,
                    "similarity":
                        1 - distance,
                }
            )

        return results

    def delete_document(
        self,
        document_id: str
    ) -> None:
        self.collection.delete(
            where={
                "document_id": document_id
            }
        )

    def count(self) -> int:
        return self.collection.count()
