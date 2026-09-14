from rag.context_builder import build_context
from rag.hybrid_retriever import HybridRetriever
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
            hybrid_retriever: HybridRetriever | None = None,
            llm_service: LLMService | None = None,
    ):
        self.retriever = (
                retriever
                or Retriever()
        )

        self.hybrid_retriever = (
                hybrid_retriever
                or HybridRetriever(
            dense_retriever=self.retriever
        )
        )

        self.llm_service = (
                llm_service
                or LLMService()
        )

    def _retrieve(
            self,
            question: str,
            document_id: str | None,
            top_k: int,
            similarity_threshold: float | None,
    ) -> tuple[list[dict], str, float | None]:
        """
        根据问答模式选择检索策略。

        指定文档：
            Dense Retrieval

        全部文档：
            Dense + BM25 + Weighted RRF
        """

        if document_id:
            effective_threshold = (
                similarity_threshold
                if similarity_threshold is not None
                else 0.45
            )

            results = self.retriever.retrieve(
                query=question,
                top_k=top_k,
                document_id=document_id,
                similarity_threshold=(
                    effective_threshold
                ),
            )

            return (
                results,
                "dense",
                effective_threshold,
            )

        results = (
            self.hybrid_retriever.retrieve(
                query=question,
                top_k=top_k,
                document_id=None,
            )
        )

        return (
            results,
            "hybrid",
            None,
        )

    def answer(
            self,
            question: str,
            document_id: str | None = None,
            top_k: int | None = None,
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

        effective_top_k = (
            top_k
            if top_k is not None
            else (
                5
                if document_id
                else 8
            )
        )

        retrieval_results, _, _ = (
            self._retrieve(
                question=question,
                document_id=document_id,
                top_k=effective_top_k,
                similarity_threshold=(
                    similarity_threshold
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
            top_k: int | None = None,
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

        effective_top_k = (
            top_k
            if top_k is not None
            else (
                5
                if document_id
                else 8
            )
        )

        retrieval_results, _, _ = (
            self._retrieve(
                question=question,
                document_id=document_id,
                top_k=effective_top_k,
                similarity_threshold=(
                    similarity_threshold
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