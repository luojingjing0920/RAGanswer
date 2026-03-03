/**
 * 本地后端API服务
 * 用于调用本地8000端口后端接口
 */
class ApiService {
  constructor() {
    // API基础URL，指向本地8000端口后端服务
    this.baseUrl = 'http://localhost:8000';
  }
  
  /**
   * 上传文档文件
   * @param {File} file - 要上传的文件对象
   * @param {Object} options - 上传选项
   * @returns {Promise<Object>} 上传结果
   */
  async uploadDocument(file, options = {}) {
    try {
      // 使用FormData来构建多部分表单数据
      const formData = new FormData();
      formData.append('file', file);
      formData.append('need_summary', options.needSummary?.toString() || 'false');
      formData.append('step_by_step', options.stepByStep?.toString() || 'false');
      
      // 如果有回调URL，添加到表单数据中
      if (options.callbackUrl) {
        formData.append('callback_url', options.callbackUrl);
      }
      
      // 调用本地8000端口的上传文档接口
      const response = await fetch(`${this.baseUrl}/api/upload-document`, {
        method: 'POST',
        // 注意：不要手动设置Content-Type，让浏览器自动处理multipart/form-data
        body: formData
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`文件上传失败: ${response.status} ${errorText}`);
        throw new Error(`文件上传失败: ${response.status} ${errorText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('文档上传失败:', error);
      throw error;
    }
  }

  /**
   * 文档问答
   * @param {string} fileId - 文件ID
   * @param {string} question - 问题
   * @returns {Promise<Object>} 问答结果
   */
  async askQuestion(fileId, question) {
    try {
      // 设置超时控制
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60秒超时
      
      // 调用本地8000端口的文档问答接口
      const response = await fetch(`${this.baseUrl}/api/qa-document`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          file_id: fileId,
          question: question
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId); // 清除超时定时器
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`文档问答失败: ${response.status} ${errorText}`);
        throw new Error(`文档问答失败: ${response.status} ${errorText}`);
      }

      const data = await response.json();
      // 优先使用answer字段，如果没有再使用完整响应
      return data.answer || data.content || data;
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('请求超时，请稍后重试');
      }
      console.error('文档问答失败:', error);
      throw error;
    }
  }

  /**
   * 健康检查
   * @returns {Promise<Object>} 健康检查结果
   */
  async healthCheck() {
    try {
      // 调用本地8000端口的健康检查接口
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET'
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`健康检查失败: ${response.status} ${errorText}`);
        throw new Error(`健康检查失败: ${response.status} ${errorText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('健康检查失败:', error);
      throw error;
    }
  }
}

export default new ApiService();