from rag.embeddings import EmbeddingService
from rag.vector_store import VectorStore


class Retriever:
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

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
        similarity_threshold: float = 0.4,
    ) -> list[dict]:
        """
        根据用户问题检索最相关的文档片段。
        """

        query = query.strip()

        if not query:
            raise ValueError("query 不能为空")

        query_embedding = (
            self.embedding_service
            .embed_query(query)
        )

        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            document_id=document_id,
        )

        filtered_results = [
            item
            for item in results
            if item["similarity"]
            >= similarity_threshold
        ]

        return filtered_results