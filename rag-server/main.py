# -*- coding:utf-8 -*-
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import time
import json
import os
import requests

# 导入现有的功能模块
from Document_upload import Document_Upload
from Document_Q_And_A import Document_Q_And_A
from dotenv import load_dotenv

from pathlib import Path
import tempfile

from rag.ingestion_service import (
    IngestionService,
)

load_dotenv()

# 创建FastAPI应用实例
app = FastAPI(
    title="文档问答系统API",
    description="支持本地文件上传到讯飞星火文档服务\n" +
    "- **文档问答**: 基于已上传的文档内容进行智能问答\n" +
    "\n" +
    "### 使用说明\n" +
    "1. 首先通过`/api/upload-document`接口上传文档获取fileId\n" +
    "2. 然后使用获取的fileId通过`/api/qa-document`接口进行问答",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 应用配置 - 建议从环境变量或配置文件读取
APP_ID = os.getenv("XFYUN_APP_ID")  # 示例ID，实际使用中应该从配置获取
API_SECRET = os.getenv("XFYUN_API_SECRET")  # 示例密钥，实际使用中应该从配置获取
UPLOAD_URL = "https://chatdoc.xfyun.cn/openapi/v1/file/upload"
CHAT_URL = "wss://chatdoc.xfyun.cn/openapi/chat"
if not APP_ID or not API_SECRET:
    raise RuntimeError(
        "Missing XFYUN_APP_ID or XFYUN_API_SECRET environment variables"
    )

# 请求模型
class QARequest(BaseModel):
    file_id: str
    question: str

@app.get("/")
async def root():
    return {"message": "文档问答系统API服务运行中"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post(
    "/api/rag/documents",
    summary="上传并索引 RAG 文档",
    description=(
        "上传本地文档，并完成解析、"
        "切块、向量化及 ChromaDB 入库"
    ),
)
async def upload_rag_document(
    file: UploadFile = File(...)
):
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

    temp_path = None

    try:
        file_content = await file.read()

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
            temp_file.write(file_content)
            temp_path = Path(
                temp_file.name
            )

        ingestion_service = (
            IngestionService()
        )

        result = ingestion_service.ingest(
            temp_path,
            original_file_name=file.filename,
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

@app.post("/api/upload-document", summary="上传文档", description="上传本地文件到文档服务")
async def upload_document(
    file: UploadFile = File(...),
    need_summary: bool = Form(False),
    step_by_step: bool = Form(False),
    callback_url: str = Form(None)
):
    """
    上传文档到讯飞星火文档服务
    
    - **file**: 要上传的文件
    - **need_summary**: 是否需要摘要，默认False
    - **step_by_step**: 是否分步处理，默认False
    - **callback_url**: 回调URL，可选
    """
    try:
        # 生成当前时间戳
        cur_time = str(int(time.time()))
        
        # 创建上传实例
        document_upload = Document_Upload(APP_ID, API_SECRET, cur_time)
        headers = document_upload.get_header()
        
        # 准备请求体和文件
        body = {
            "url": "",
            "fileName": file.filename,
            "fileType": "wiki",
            "needSummary": need_summary,
            "stepByStep": step_by_step,
            "callbackUrl": callback_url or "",
        }
        
        # 读取文件内容
        file_content = await file.read()
        files = {'file': (file.filename, file_content)}
        
        # 发送请求
        response = requests.post(UPLOAD_URL, files=files, data=body, headers=headers)
        response.raise_for_status()  # 检查请求是否成功
        
        return response.json()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")

import websocket
import _thread as thread
import ssl
from fastapi.responses import StreamingResponse
import asyncio
from io import StringIO
import queue
import threading

# 流式输出

@app.post(
    "/api/qa-document",
    summary="文档问答",
    description="基于上传的文档进行问答"
)
async def qa_document(request: QARequest):
    """
    基于上传的文档进行问答

    - **file_id**: 上传文档返回的fileId
    - **question**: 用户的问题
    """
    try:
        # 生成当前时间戳
        cur_time = str(int(time.time()))

        # 创建问答实例
        document_qa = Document_Q_And_A(
            APP_ID,
            API_SECRET,
            cur_time,
            CHAT_URL
        )

        # 准备请求体
        body = {
            "chatExtends": {
                "wikiPromptTpl": (
                    "请将以下内容作为已知信息：\n"
                    "<wikicontent>\n"
                    "请根据以上内容回答用户的问题。\n"
                    "问题:<wikiquestion>\n"
                    "回答:"
                ),
                "wikiFilterScore": 0.83,
                "temperature": 0.5
            },
            "fileIds": [request.file_id],
            "messages": [
                {
                    "role": "user",
                    "content": request.question
                }
            ]
        }

        # 获取 WebSocket URL
        ws_url = document_qa.get_url()

        # 调用旧版同步 WebSocket 函数
        result = await asyncio.to_thread(
            process_websocket_request,
            ws_url,
            body
        )

        # 等待完整答案后一次性返回
        return {"answer": result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"文档问答失败: {str(e)}"
        )

@app.post(
    "/api/qa-document-stream",
    summary="流式文档问答",
    description="基于上传的文档进行流式问答"
)
async def qa_document_stream(request: QARequest):
    """
    基于上传的文档进行流式问答

    - **file_id**: 上传文档返回的fileId
    - **question**: 用户的问题
    """
    try:
        # 生成当前时间戳
        cur_time = str(int(time.time()))

        # 创建问答实例
        document_qa = Document_Q_And_A(
            APP_ID,
            API_SECRET,
            cur_time,
            CHAT_URL
        )

        # 准备请求体
        body = {
            "chatExtends": {
                "wikiPromptTpl": (
                    "请将以下内容作为已知信息：\n"
                    "<wikicontent>\n"
                    "请根据以上内容回答用户的问题。\n"
                    "问题:<wikiquestion>\n"
                    "回答:"
                ),
                "wikiFilterScore": 0.83,
                "temperature": 0.5
            },
            "fileIds": [request.file_id],
            "messages": [
                {
                    "role": "user",
                    "content": request.question
                }
            ]
        }

        # 获取 WebSocket URL
        ws_url = document_qa.get_url()

        # 获取流式 generator
        stream = stream_websocket_response(
            ws_url,
            body
        )

        # 持续向浏览器发送 chunk
        return StreamingResponse(
            stream,
            media_type="text/plain; charset=utf-8"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"流式文档问答失败: {str(e)}"
        )

# 处理WebSocket请求的函数
def process_websocket_request(ws_url, body):
    result_buffer = []

    def on_message(ws, message):
        data = json.loads(message)
        code = data['code']

        if code != 0:
            print(f'请求错误: {code}, {data}')
            ws.close()
        else:
            content = data["content"]
            status = data["status"]

            result_buffer.append(content)

            if status == 2:
                ws.close()

    def on_error(ws, error):
        print(f"WebSocket错误: {error}")
        result_buffer.append(f"错误: {str(error)}")

    def on_close(ws, close_status_code, close_msg):
        print("WebSocket连接关闭")

    def on_open(ws):
        def run(*args):
            data = json.dumps(body)
            ws.send(data)

        thread.start_new_thread(run, ())

    websocket.enableTrace(False)

    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )

    ws.run_forever(
        sslopt={"cert_reqs": ssl.CERT_NONE}
    )

    return ''.join(result_buffer)
def stream_websocket_response(ws_url, body):
    message_queue = queue.Queue()
    END = object()

    def on_message(ws, message):
        data = json.loads(message)
        code = data.get("code")

        if code != 0:
            print(f"请求错误: {code}, {data}")

            error_message = (
                    data.get("content")
                    or data.get("message")
                    or "文档问答失败，请稍后重试"
            )

            message_queue.put(error_message)
            message_queue.put(END)

            ws.close()
            return

        else:
            content = data.get("content")
            status = data.get("status")

            if content:
                message_queue.put(content)

            if status == 2:
                message_queue.put(END)
                ws.close()

    def on_error(ws, error):
        print(f"WebSocket错误: {error}")
        message_queue.put(f"错误: {str(error)}")
        message_queue.put(END)
        ws.close()

    def on_close(ws, close_status_code, close_msg):
        print("WebSocket连接关闭")
        message_queue.put(END)

    def on_open(ws):
        def run(*args):
            data = json.dumps(body)
            ws.send(data)

        thread.start_new_thread(run, ())

    def generate():
        while True:
            item = message_queue.get()

            if item is END:
                break

            yield item

    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )

    def run_websocket():
        ws.run_forever(
            sslopt={"cert_reqs": ssl.CERT_NONE}
        )

    ws_thread = threading.Thread(
        target=run_websocket,
        daemon=True
    )

    ws_thread.start()

    return generate()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)