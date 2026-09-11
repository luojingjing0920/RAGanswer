/**
 * 自建 RAG 后端 API 服务
 */
class ApiService {
  constructor() {
    this.baseUrl =
      import.meta.env.VITE_API_BASE_URL ||
      'http://127.0.0.1:8001';
  }

  /**
   * 上传并索引文档
   *
   * Document
   * → Parser
   * → Chunker
   * → Embedding
   * → ChromaDB
   */
  async uploadDocument(file) {
    try {
      const formData = new FormData();

      formData.append('file', file);

      const response = await fetch(
        `${this.baseUrl}/api/rag/documents`,
        {
          method: 'POST',
          body: formData
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => null);

        throw new Error(
          errorData?.detail ||
          `文件上传失败: ${response.status}`
        );
      }

      return await response.json();

    } catch (error) {
      console.error(
        'RAG 文档上传失败:',
        error
      );

      throw error;
    }
  }

  /**
 * 删除已经索引的 RAG 文档
 */
  async deleteDocument(documentId) {
    if (!documentId) {
      throw new Error(
        'documentId 不能为空'
      );
    }

    const response = await fetch(
      `${this.baseUrl
      }/api/rag/documents/${encodeURIComponent(
        documentId
      )
      }`,
      {
        method: 'DELETE'
      }
    );

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => null);

      throw new Error(
        errorData?.detail ||
        `删除文档失败: ${response.status
        }`
      );
    }

    return await response.json();
  }

  /**
   * 非流式 RAG 问答
   */
  async askQuestion(
    documentId,
    question,
    options = {}
  ) {
    const response = await fetch(
      `${this.baseUrl}/api/rag/qa`,
      {
        method: 'POST',

        headers: {
          'Content-Type':
            'application/json'
        },

        body: JSON.stringify({
          document_id: documentId,
          question,
          top_k: options.topK ?? 4,
        })
      }
    );

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => null);

      throw new Error(
        errorData?.detail ||
        `RAG 问答失败: ${response.status}`
      );
    }

    return await response.json();
  }

  /**
   * 流式 RAG 问答
   *
   * 后端返回 NDJSON：
   *
   * {"type":"sources", ...}
   * {"type":"answer", ...}
   * {"type":"answer", ...}
   * {"type":"done"}
   */
  async askQuestionStream(
    documentId,
    question,
    onChunk,
    onSources,
    options = {}
  ) {
    const controller =
      new AbortController();

    const timeoutId = setTimeout(
      () => controller.abort(),
      120000
    );

    try {
      const response = await fetch(
        `${this.baseUrl}/api/rag/qa-stream`,
        {
          method: 'POST',

          headers: {
            'Content-Type':
              'application/json'
          },

          body: JSON.stringify({
            document_id: documentId,
            question,
            top_k:
              options.topK ?? 4,
          }),

          signal: controller.signal
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => null);

        throw new Error(
          errorData?.detail ||
          `RAG 流式问答失败: ${response.status
          }`
        );
      }

      if (!response.body) {
        throw new Error(
          '当前浏览器不支持流式响应'
        );
      }

      const reader =
        response.body.getReader();

      const decoder =
        new TextDecoder('utf-8');

      let buffer = '';
      let fullText = '';
      let sources = [];

      /**
       * 处理一整行 NDJSON。
       */
      const handleLine = (line) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return;
        }

        let event;

        try {
          event = JSON.parse(trimmed);
        } catch (error) {
          console.error(
            'NDJSON 解析失败:',
            trimmed,
            error
          );

          throw new Error(
            '流式响应格式解析失败'
          );
        }

        if (event.type === 'sources') {
          sources = Array.isArray(
            event.data
          )
            ? event.data
            : [];

          if (onSources) {
            onSources(sources);
          }

          return;
        }

        if (event.type === 'answer') {
          const delta =
            event.delta || '';

          fullText += delta;

          if (onChunk) {
            onChunk(
              delta,
              fullText
            );
          }

          return;
        }

        if (event.type === 'error') {
          throw new Error(
            event.message ||
            'RAG 流式生成失败'
          );
        }

        // done 事件暂时不需要额外处理
      };

      while (true) {
        const {
          done,
          value
        } = await reader.read();

        if (done) {
          break;
        }

        /**
         * 注意：
         * 一个网络 chunk
         * 不一定刚好等于一行 JSON。
         *
         * 所以必须使用 buffer。
         */
        buffer += decoder.decode(
          value,
          {
            stream: true
          }
        );

        const lines =
          buffer.split('\n');

        /**
         * 最后一段可能只有半个 JSON，
         * 留到下一次网络数据继续拼。
         */
        buffer =
          lines.pop() || '';

        for (const line of lines) {
          handleLine(line);
        }
      }

      /**
       * 清空 TextDecoder
       * 剩余缓冲内容。
       */
      buffer += decoder.decode();

      if (buffer.trim()) {
        handleLine(buffer);
      }

      return {
        answer: fullText,
        sources
      };

    } catch (error) {
      if (
        error.name === 'AbortError'
      ) {
        throw new Error(
          '请求超时，请稍后重试'
        );
      }

      console.error(
        'RAG 流式问答失败:',
        error
      );

      throw error;

    } finally {
      clearTimeout(timeoutId);
    }
  }

  async healthCheck() {
    const response = await fetch(
      `${this.baseUrl}/health`
    );

    if (!response.ok) {
      throw new Error(
        `健康检查失败: ${response.status
        }`
      );
    }

    return await response.json();
  }
}

export default new ApiService();