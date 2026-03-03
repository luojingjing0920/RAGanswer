# 文档问答系统API

本项目将文档上传和文档问答功能封装为FastAPI服务，提供RESTful API供前端调用。

## 功能特性

- **文档上传**: 支持上传本地文件到讯飞星火文档服务
- **文档问答**: 基于已上传的文档内容进行智能问答
- **自动文档**: 集成Swagger UI和ReDoc，提供交互式API文档
- **CORS支持**: 配置跨域资源共享，方便前端调用

## 快速开始

### 1. 环境准备

```bash
# 克隆项目（如果是从代码仓库获取）
# git clone <repository-url>

# 进入项目目录
cd rag-server

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置应用

在`main.py`文件中，需要配置讯飞星火的应用信息：

```python
# 应用配置 - 建议从环境变量或配置文件读取
APP_ID = "你的APPID"  # 从讯飞开放平台获取
API_SECRET = "你的API_SECRET"  # 从讯飞开放平台获取
```

### 3. 启动服务

方法一：使用启动脚本（推荐）

```bash
python start_server.py
```

方法二：直接运行

```bash
python main.py
```

服务启动后，可访问以下地址：
- 服务首页: http://localhost:8000
- Swagger API文档: http://localhost:8000/docs
- ReDoc API文档: http://localhost:8000/redoc

## API接口文档

### 1. 上传文档

**POST** `/api/upload-document`

**请求参数**：
- `file`: 文件（multipart/form-data格式）
- `need_summary` (可选): 是否需要摘要，默认false
- `step_by_step` (可选): 是否分步处理，默认false
- `callback_url` (可选): 回调URL

**响应示例**：
```json
{
  "code": 0,
  "desc": "success",
  "fileId": "文件ID",
  "data": {
    "fileId": "文件ID",
    "fileName": "文件名",
    "fileSize": 1024,
    "fileType": "wiki",
    "status": 2
  }
}
```

### 2. 文档问答

**POST** `/api/qa-document`

**请求体** (application/json)：
```json
{
  "file_id": "文件ID",
  "question": "你的问题"
}
```

**响应示例**：
```json
{
  "answer": "基于文档内容的回答..."
}
```

### 3. 健康检查

**GET** `/health`

**响应示例**：
```json
{
  "status": "healthy"
}
```

## 前端调用示例

### 使用Fetch API上传文档

```javascript
async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('need_summary', 'false');
  formData.append('step_by_step', 'false');
  
  try {
    const response = await fetch('http://localhost:8000/api/upload-document', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    return result;
  } catch (error) {
    console.error('上传失败:', error);
  }
}
```

### 使用Fetch API进行文档问答

```javascript
async function askQuestion(fileId, question) {
  try {
    const response = await fetch('http://localhost:8000/api/qa-document', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        file_id: fileId,
        question: question
      })
    });
    
    const result = await response.json();
    return result.answer;
  } catch (error) {
    console.error('问答失败:', error);
  }
}
```

## 注意事项

1. 请确保使用正确的讯飞星火应用ID和密钥
2. 在生产环境中，请配置具体的CORS允许域名，不要使用通配符
3. 建议将敏感配置（如APP_ID、API_SECRET）通过环境变量或配置文件管理
4. 本服务使用8000端口，确保该端口未被占用

## 依赖列表

- fastapi
- uvicorn
- requests
- websocket-client
- requests-toolbelt
- python-multipart

## 许可证

MIT