from fastembed import TextEmbedding


MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)


class EmbeddingService:
    """
    文本向量化服务。

    负责将：
    - 文档 chunk
    - 用户 query

    转换为统一维度的语义向量。
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME
    ):
        self.model_name = model_name

        self.model = TextEmbedding(
            model_name=model_name
        )

    def embed_texts(
        self,
        texts: list[str]
    ) -> list[list[float]]:
        """
        批量生成文档文本向量。
        """

        if not texts:
            return []

        embeddings = list(
            self.model.embed(texts)
        )

        return [
            embedding.tolist()
            for embedding in embeddings
        ]

    def embed_query(
        self,
        query: str
    ) -> list[float]:
        """
        生成用户问题的查询向量。
        """

        query = query.strip()

        if not query:
            raise ValueError("query 不能为空")

        embeddings = list(
            self.model.embed([query])
        )

        return embeddings[0].tolist()