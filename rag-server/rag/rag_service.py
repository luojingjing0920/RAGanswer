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
        top_k: int = 3,
        similarity_threshold: float = 0.5,
    ) -> dict:
        """
        根据知识库文档回答问题。
        """

        question = question.strip()

        if not question:
            raise ValueError(
                "question 不能为空"
            )

        retrieval_results = (
            self.retriever.retrieve(
                query=question,
                top_k=top_k,
                document_id=document_id,
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
            top_k: int = 3,
            similarity_threshold: float = 0.5,
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

        retrieval_results = (
            self.retriever.retrieve(
                query=question,
                top_k=top_k,
                document_id=document_id,
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

        # 先告诉前端本次回答引用了哪些资料。
        yield {
            "type": "sources",
            "data": sources,
        }

        # 再持续输出模型回答。
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