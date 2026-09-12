# -*- coding: utf-8 -*-

import asyncio
import json
import tempfile
from pathlib import Path

import uvicorn
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rag.ingestion_service import IngestionService
from rag.rag_service import RAGService
from rag.vector_store import VectorStore


# =========================
# FastAPI Application
# =========================

app = FastAPI(
    title="RAG 智能文档问答系统 API",
    description=(
        "基于自建 RAG Pipeline 的智能文档问答服务。\n\n"
        "### 核心流程\n"
        "Document Parsing → Chunking → Embedding → "
        "ChromaDB → Top-K Retrieval → Context Building → "
        "LLM Generation\n\n"
        "### 主要能力\n"
        "- 支持 PDF / DOCX / TXT / MD 文档解析与索引\n"
        "- 支持当前文档与跨文档语义检索\n"
        "- 支持动态相似度阈值过滤\n"
        "- 支持低相关问题拒答\n"
        "- 支持 LLM 流式回答\n"
        "- 支持可追溯的参考来源\n"
    ),
    version="2.0.0",
)


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Request Models
# =========================

class RAGQARequest(BaseModel):
    """
    RAG 问答请求模型。

    document_id:
        有值 -> 只检索当前文档
        None -> 检索整个知识库

    similarity_threshold:
        默认由 RAGService 根据检索范围动态决定。
        主要保留用于调试或手动覆盖。
    """

    document_id: str | None = None
    question: str
    top_k: int = 4
    similarity_threshold: float | None = None


# =========================
# Basic Routes
# =========================

@app.get(
    "/",
    summary="服务信息",
)
async def root():
    return {
        "name": "RAG 智能文档问答系统",
        "version": "2.0.0",
        "status": "running",
    }


@app.get(
    "/health",
    summary="健康检查",
)
async def health_check():
    return {
        "status": "healthy",
    }


# =========================
# Document Ingestion
# =========================

@app.get(
    "/api/rag/documents",
    summary="获取 RAG 文档列表",
    description=(
        "获取当前 ChromaDB 中"
        "已经索引的文档列表"
    ),
)
async def list_rag_documents():
    """
    ChromaDB
        ↓
    Chunk Metadata
        ↓
    document_id 聚合
        ↓
    Document List
    """

    try:
        vector_store = VectorStore()

        documents = await asyncio.to_thread(
            vector_store.list_documents
        )

        return {
            "status": "success",
            "count": len(documents),
            "documents": documents,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"获取文档列表失败：{exc}"
            ),
        ) from exc

@app.post(
    "/api/rag/documents",
    summary="上传并索引 RAG 文档",
    description=(
        "上传本地文档，并完成解析、切块、"
        "向量化及 ChromaDB 入库。"
    ),
)
async def upload_rag_document(
    file: UploadFile = File(...),
):
    """
    文档索引流程：

    Upload
        ↓
    Temporary File
        ↓
    Document Parser
        ↓
    Chunker
        ↓
    Embedding
        ↓
    ChromaDB
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="文件名不能为空",
        )

    suffix = Path(
        file.filename
    ).suffix.lower()

    supported_extensions = {
        ".pdf",
        ".docx",
        ".txt",
        ".md",
    }

    if suffix not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                "暂不支持该文件类型，"
                "仅支持 PDF、DOCX、TXT、MD"
            ),
        )

    temp_path: Path | None = None

    try:
        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="上传文件为空",
            )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
            temp_file.write(
                file_content
            )

            temp_path = Path(
                temp_file.name
            )

        ingestion_service = (
            IngestionService()
        )

        # 文档解析、Embedding 等操作属于
        # 同步阻塞任务，放到线程池中执行，
        # 避免阻塞 FastAPI Event Loop。
        result = await asyncio.to_thread(
            ingestion_service.ingest,
            temp_path,
            original_file_name=(
                file.filename
            ),
        )

        return {
            "status": "success",
            **result,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"文档索引失败：{exc}"
            ),
        ) from exc

    finally:
        if (
            temp_path is not None
            and temp_path.exists()
        ):
            temp_path.unlink(
                missing_ok=True
            )


# =========================
# Document Deletion
# =========================

@app.delete(
    "/api/rag/documents/{document_id}",
    summary="删除 RAG 文档",
    description=(
        "删除指定文档在 ChromaDB 中"
        "保存的 Chunk 与向量数据。"
    ),
)
async def delete_rag_document(
    document_id: str,
):
    """
    删除指定文档的所有向量索引。
    """

    document_id = (
        document_id.strip()
    )

    if not document_id:
        raise HTTPException(
            status_code=400,
            detail="document_id 不能为空",
        )

    try:
        vector_store = VectorStore()

        await asyncio.to_thread(
            vector_store.delete_document,
            document_id,
        )

        return {
            "status": "success",
            "document_id": document_id,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"删除文档失败：{exc}"
            ),
        ) from exc


# =========================
# Non-streaming RAG QA
# =========================

@app.post(
    "/api/rag/qa",
    summary="RAG 文档问答",
    description=(
        "基于自建 Retrieval Pipeline "
        "和 LLM 回答文档问题。"
    ),
)
async def rag_qa(
    request: RAGQARequest,
):
    """
    Question
        ↓
    Query Embedding
        ↓
    Chroma Top-K Retrieval
        ↓
    Similarity Threshold
        ↓
    Context Builder
        ↓
    LLM
        ↓
    Answer + Sources
    """

    try:
        rag_service = RAGService()

        result = await asyncio.to_thread(
            rag_service.answer,
            request.question,
            request.document_id,
            request.top_k,
            request.similarity_threshold,
        )

        return {
            "status": "success",
            **result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"RAG 问答失败：{exc}"
            ),
        ) from exc


# =========================
# Streaming RAG QA
# =========================

@app.post(
    "/api/rag/qa-stream",
    summary="RAG 流式文档问答",
    description=(
        "基于自建 Retrieval Pipeline "
        "进行流式文档问答，"
        "响应格式为 NDJSON。"
    ),
)
async def rag_qa_stream(
    request: RAGQARequest,
):
    """
    NDJSON Protocol：

    sources
        ↓
    answer
        ↓
    answer
        ↓
    ...
        ↓
    done
    """

    def generate():
        try:
            rag_service = (
                RAGService()
            )

            for event in (
                rag_service.answer_stream(
                    question=(
                        request.question
                    ),
                    document_id=(
                        request.document_id
                    ),
                    top_k=(
                        request.top_k
                    ),
                    similarity_threshold=(
                        request
                        .similarity_threshold
                    ),
                )
            ):
                yield (
                    json.dumps(
                        event,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        except Exception as exc:
            error_event = {
                "type": "error",
                "message": str(exc),
            }

            yield (
                json.dumps(
                    error_event,
                    ensure_ascii=False,
                )
                + "\n"
            )

    return StreamingResponse(
        generate(),
        media_type=(
            "application/x-ndjson; "
            "charset=utf-8"
        ),
    )


# =========================
# Local Development
# =========================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
    )

