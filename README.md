# RAG智能文档问答系统

基于 **检索增强生成（RAG）** 技术的智能文档问答系统，前端使用 **Vue 3**，后端使用 **FastAPI**，并集成 **讯飞星火大模型** 的文档服务，实现对上传文档的智能问答。

https://img.shields.io/badge/license-MIT-blue.svg
https://img.shields.io/badge/vue-3.4.21-brightgreen
https://img.shields.io/badge/FastAPI-0.115.0-009688

------

## 功能特性

- 📄 **文档上传**：支持 `.doc`、`.docx`、`.pdf`、`.md`、`.txt` 格式，最大 20MB，可拖拽或点击上传。
- ⚙️ **上传选项**：可选择是否需要摘要、是否分步处理文档。
- 💬 **智能问答**：基于已上传文档的内容，通过讯飞星火大模型生成精准回答。
- 📜 **对话历史**：显示问答对话记录，支持清空对话。
- 🗂️ **历史文档管理**：上传过的文档保存在本地，可快速切换使用。
- 🎨 **现代化 UI**：渐变背景、动画过渡、响应式设计，支持深色/浅色模式。

------

## 技术栈

### 前端

- **Vue 3** + **Vite** – 快速开发与构建
- **JavaScript (ES6)** – 核心逻辑
- **CSS3** – 样式与动画（无第三方UI库）
- **LocalStorage** – 存储历史文档

### 后端

- **FastAPI** – 高性能异步 Web 框架
- **Uvicorn** – ASGI 服务器
- **Python 3.9+**
- **讯飞星火文档服务 API** – 文档上传与问答接口
- **依赖库**：`requests`, `websocket-client`, `requests-toolbelt`

------

## 快速开始

### 1. 克隆仓库

bash

```
git clone https://github.com/yourusername/rag-doc-qa.git
cd rag-doc-qa
```



### 2. 前端运行

bash

```
cd frontend          # 假设前端代码在 frontend 目录（实际项目在根目录的 src）
npm install
npm run dev
```



前端默认运行在 `http://localhost:5173`。

> ⚠️ 注意：如果项目结构不同，请根据实际情况调整路径。

### 3. 后端运行

#### 安装 Python 依赖

bash

```
cd backend           # 后端代码在 backend 目录（实际项目在根目录）
pip install fastapi uvicorn requests websocket-client requests-toolbelt
```



#### 配置讯飞应用凭证

在 `main.py` 中替换以下变量为你的讯飞应用信息：

python

```
APP_ID = "你的APP_ID"
API_SECRET = "你的API_SECRET"
```



> 你可以在 [讯飞开放平台控制台](https://console.xfyun.cn/) 创建应用获取这些信息。

#### 启动后端服务

bash

```
python start_server.py
```



或直接：

bash

```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```



后端服务将运行在 `http://localhost:8000`，自动重启。

### 4. 访问系统

打开浏览器访问 `http://localhost:5173` 即可使用。

------

## API 文档

启动后端后，可访问 `http://localhost:8000/docs` 查看自动生成的 Swagger 交互式 API 文档。

### 主要接口

- **POST** `/api/upload-document` – 上传本地文档
  - 参数：`file` (文件), `need_summary` (bool), `step_by_step` (bool), `callback_url` (可选)
  - 返回：包含 `fileId` 的上传结果
- **POST** `/api/qa-document` – 文档问答
  - 请求体：`{ "file_id": "xxx", "question": "问题" }`
  - 返回：`{ "answer": "回答内容" }`
- **GET** `/health` – 健康检查

------

## 项目结构

text

```
.
├── src/                     # 前端源码
│   ├── components/          # Vue组件（FileUpload, DocumentQA）
│   ├── views/               # 主页面（MainPage.vue）
│   ├── services/            # API服务（apiService.js, authService.js等）
│   ├── App.vue
│   └── main.js
├── backend/                  # 后端源码（根据实际情况调整路径）
│   ├── main.py               # FastAPI主应用
│   ├── Document_upload.py    # 上传功能封装
│   ├── Document_Q_And_A.py   # 问答功能封装
│   ├── start_server.py       # 启动脚本
│   └── ...
├── index.html                # 前端入口
├── package.json
├── README.md                 # 本文档
└── ...
```



------

## 环境变量与配置

- 前端 API 基础地址在 `src/services/apiService.js` 中配置（默认为 `http://localhost:8000`）。
- 后端 `APP_ID` 和 `API_SECRET` 需替换为实际值，建议使用环境变量或配置文件避免硬编码。

------

## 贡献指南

欢迎提交 Issue 和 Pull Request。请确保代码风格一致，并添加必要的注释。

------

## 许可证

[MIT](https://license/)

------

## 致谢

- 感谢 [讯飞开放平台](https://www.xfyun.cn/) 提供的文档服务 API。
- 感谢 Vue 和 FastAPI 社区的优秀作品。