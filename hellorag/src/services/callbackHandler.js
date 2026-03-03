/**
 * 回调处理器
 * 用于在前端环境中模拟处理服务端回调请求
 * 在实际生产环境中，这部分逻辑应该在后端实现
 */

import apiService from './apiService';

class CallbackHandler {
  /**
   * 初始化回调处理
   * 监听页面加载时的URL参数，模拟回调请求
   */
  static init() {
    // 检查URL中是否包含fileId和fileStatus参数，如果有则处理为模拟的回调请求
    const urlParams = new URLSearchParams(window.location.search);
    const fileId = urlParams.get('fileId');
    const fileStatus = urlParams.get('fileStatus');
    
    // 如果检测到回调参数，处理回调
    if (fileId && fileStatus) {
      console.log('检测到模拟回调请求参数:', { fileId, fileStatus });
      // 使用当前页面的请求头作为回调请求的头信息
      this.handleCallback({ fileId, fileStatus }, window.document.headers || {});
    }
  }

  /**
   * 处理回调请求
   * @param {Object} params - 回调参数，包含fileId和fileStatus
   * @param {Object} headers - 请求头
   */
  static async handleCallback(params, headers) {
    try {
      console.log('开始处理回调请求:', params);
      
      // 调用apiService中的handleCallback方法处理回调
      const result = await apiService.handleCallback(params, headers);
      
      if (result.success) {
        console.log('回调处理成功:', result);
        // 这里可以触发文件状态更新事件
        this.triggerFileStatusUpdate(result.fileId, result.fileStatus);
      } else {
        console.error('回调处理失败:', result.error);
      }
    } catch (error) {
      console.error('处理回调时发生错误:', error);
    }
  }

  /**
   * 触发文件状态更新事件
   * @param {string} fileId - 文件ID
   * @param {string} fileStatus - 文件状态
   */
  static triggerFileStatusUpdate(fileId, fileStatus) {
    // 创建并分发自定义事件
    const event = new CustomEvent('fileStatusUpdate', {
      detail: {
        fileId,
        fileStatus,
        timestamp: Date.now()
      }
    });
    
    // 派发事件到window对象
    window.dispatchEvent(event);
    
    console.log(`已触发文件状态更新事件: fileId=${fileId}, status=${fileStatus}`);
  }

  /**
   * 注册文件状态更新监听器
   * @param {Function} callback - 回调函数，接收文件状态更新信息
   * @returns {Function} 取消监听的函数
   */
  static onFileStatusUpdate(callback) {
    const handleEvent = (event) => {
      callback(event.detail);
    };
    
    window.addEventListener('fileStatusUpdate', handleEvent);
    
    // 返回取消监听的函数
    return () => {
      window.removeEventListener('fileStatusUpdate', handleEvent);
    };
  }

  /**
   * 创建模拟回调URL
   * 用于测试回调功能
   * @param {string} fileId - 文件ID
   * @param {string} fileStatus - 文件状态
   * @returns {string} 模拟回调URL
   */
  static createMockCallbackUrl(fileId, fileStatus) {
    return `${window.location.origin}${window.location.pathname}?fileId=${fileId}&fileStatus=${fileStatus}`;
  }
}

// 导出CallbackHandler类
export default CallbackHandler;

// 在模块加载时自动初始化
if (typeof window !== 'undefined') {
  window.addEventListener('load', () => {
    CallbackHandler.init();
  });
}