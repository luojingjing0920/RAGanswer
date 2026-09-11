from rag.context_builder import build_context
from rag.llm_service import LLMService
from rag.retriever import Retriever


class RAGService:
    """
    RAG 核心编排服务。

    完整流程：

    Question
        ↓
    Retriever
        ↓
    Similarity Threshold
        ↓
    Context Builder
        ↓
    LLM
        ↓
    Answer + Sources
    """

    def __init__(
        self,
        retriever: Retriever | None = None,
        llm_service: LLMService | None = None,
    ):
        self.retriever = (
            retriever
            or Retriever()
        )

        self.llm_service = (
            llm_service
            or LLMService()
        )

    def answer(
            self,
            question: str,
            document_id: str | None = None,
            top_k: int = 4,
            similarity_threshold: float | None = None,
    ) -> dict:
        """
        根据知识库文档回答问题。
        """

        question = question.strip()

        if not question:
            raise ValueError(
                "question 不能为空"
            )

        # 当前文档模式：
        # 已经通过 document_id 限定了搜索范围，
        # 因此使用更宽松的阈值，提高召回率。
        #
        # 全部文档模式：
        # 搜索空间更大，使用稍高阈值，
        # 降低无关文档被召回的概率。
        effective_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else (
                0.05
                if document_id
                else 0.10
            )
        )

        retrieval_results = (
            self.retriever.retrieve(
                query=question,
                top_k=top_k,
                document_id=document_id,
                similarity_threshold=(
                    effective_threshold
                ),
            )
        )

        # Retrieval 没找到足够相关的证据，
        # 直接拒答，不调用 LLM。
        if not retrieval_results:
            return {
                "answer":
                    "根据当前文档无法确定。",
                "sources": [],
                "retrieval_count": 0,
            }

        context, sources = build_context(
            retrieval_results
        )

        answer = self.llm_service.generate(
            question=question,
            context=context,
        )

        return {
            "answer": answer,
            "sources": sources,
            "retrieval_count": len(
                retrieval_results
            ),
        }

    def answer_stream(
            self,
            question: str,
            document_id: str | None = None,
            top_k: int = 4,
            similarity_threshold: float | None = None,
    ):
        """
        流式 RAG 问答。

        Yield 的事件格式：

        {
            "type": "sources",
            "data": [...]
        }

        {
            "type": "answer",
            "delta": "..."
        }

        {
            "type": "done"
        }
        """

        question = question.strip()

        if not question:
            raise ValueError(
                "question 不能为空"
            )

        # 动态选择默认相似度阈值
        effective_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else (
                0.05
                if document_id
                else 0.10
            )
        )

        retrieval_results = (
            self.retriever.retrieve(
                query=question,
                top_k=top_k,
                document_id=document_id,
                similarity_threshold=(
                    effective_threshold
                ),
            )
        )

        # 没有足够证据时，
        # 直接返回拒答，不调用 LLM。
        if not retrieval_results:
            yield {
                "type": "sources",
                "data": [],
            }

            yield {
                "type": "answer",
                "delta":
                    "根据当前文档无法确定。",
            }

            yield {
                "type": "done"
            }

            return

        context, sources = build_context(
            retrieval_results
        )

        # 先发送引用来源
        yield {
            "type": "sources",
            "data": sources,
        }

        # 再流式输出模型回答
        for delta in (
                self.llm_service
                        .generate_stream(
                    question=question,
                    context=context,
                )
        ):
            yield {
                "type": "answer",
                "delta": delta,
            }

        yield {
            "type": "done"
        }