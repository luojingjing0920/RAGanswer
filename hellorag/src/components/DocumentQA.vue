<template>
  <div class="document-qa-container">
    <h3>文档问答</h3>
    
    <!-- 文件ID输入区域 -->
    <div class="file-id-section">
      <label for="fileIdInput">文件ID：</label>
      <input 
        id="fileIdInput"
        v-model="fileId" 
        type="text" 
        placeholder="请输入上传文档的文件ID"
        class="file-id-input"
      >
    </div>
    
    <!-- 问答区域 -->
    <div class="qa-section" v-if="fileId">
      <!-- 问题输入 -->
      <div class="question-input-section">
        <input 
          v-model="question" 
          type="text" 
          placeholder="请输入您的问题..."
          class="question-input"
          @keyup.enter="sendQuestion"
        >
        <button 
          @click="sendQuestion"
          :disabled="!canSendQuestion || isLoading"
          class="send-btn"
        >
          {{ isLoading ? '发送中...' : '发送' }}
        </button>
      </div>
      
      <!-- 对话历史 -->
      <div class="conversation-history" ref="conversationHistory">
        <div v-for="(message, index) in conversation" :key="index" class="message-wrapper">
          <!-- 用户消息 -->
          <div v-if="message.type === 'user'" class="message user-message">
            <div class="message-header">
              <span class="message-author">您</span>
              <span class="message-time">{{ formatTime(message.time) }}</span>
            </div>
            <div class="message-content">
              {{ message.content }}
            </div>
          </div>
          
          <!-- 系统消息 -->
          <div v-else-if="message.type === 'system'" class="message system-message">
            <div class="message-header">
              <span class="message-author">系统</span>
              <span class="message-time">{{ formatTime(message.time) }}</span>
            </div>
            <div class="message-content">
              {{ message.content }}
            </div>
          </div>
          
          <!-- AI回答 -->
          <div v-else-if="message.type === 'ai'" class="message ai-message">
            <div class="message-header">
              <span class="message-author">AI助手</span>
              <span class="message-time">{{ formatTime(message.time) }}</span>
            </div>
            <div class="message-content" v-html="formatAnswer(message.content)">
            </div>
          </div>
        </div>
        
        <!-- 正在输入提示 -->
        <div v-if="isLoading" class="message ai-message typing">
          <div class="message-header">
            <span class="message-author">AI助手</span>
          </div>
          <div class="message-content">
            <span class="typing-indicator">正在生成回答...</span>
          </div>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="qa-actions">
        <button @click="clearConversation" class="clear-btn">清空对话</button>
      </div>
    </div>
    
    <!-- 提示信息 -->
    <div v-if="!fileId" class="info-message">
      <p>请输入文件ID后开始问答</p>
    </div>
    
    <!-- 错误信息 -->
    <div v-if="error" class="error-message">
      <p>{{ error }}</p>
    </div>
  </div>
</template>

<script>
import apiService from '../services/apiService';

export default {
  name: 'DocumentQA',
  props: {
    // 可以从父组件传入文件ID
    initialFileId: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      fileId: '',
      question: '',
      conversation: [],
      error: null,
      isLoading: false
    };
  },
  computed: {
    canSendQuestion() {
      return this.question.trim() && !this.isLoading;
    }
  },
  watch: {
    initialFileId(newVal) {
      if (newVal && !this.fileId) {
        this.fileId = newVal;
      }
    }
  },
  mounted() {
    if (this.initialFileId) {
      this.fileId = this.initialFileId;
    }
  },
  methods: {
    // 发送问题
    async sendQuestion() {
      if (!this.canSendQuestion) return;
      
      const questionText = this.question.trim();
      
      // 添加用户消息到对话历史
      this.addUserMessage(questionText);
      
      this.question = '';
      this.isLoading = true;
      this.error = null;
      
      try {
        // 使用HTTP API发送问题
        const result = await apiService.askQuestion(this.fileId, questionText);
        
        // 确保我们获取的是字符串格式的回答
        let answerText = result;
        if (typeof result === 'object') {
          answerText = result.answer || result.content || JSON.stringify(result);
        } else if (typeof result !== 'string') {
          answerText = String(result);
        }
        
        // 添加AI回答到对话历史
        this.addAIMessage(answerText);
      } catch (err) {
        console.error('问答错误:', err);
        this.error = err.message || '问答失败，请稍后重试';
        this.addSystemMessage(`错误: ${this.error}`);
      } finally {
        this.isLoading = false;
      }
    },
    
    // 添加用户消息
    addUserMessage(content) {
      this.conversation.push({
        type: 'user',
        content,
        time: new Date()
      });
      this.scrollToBottom();
    },
    
    // 添加AI回答
    addAIMessage(content) {
      // 添加新消息
      this.conversation.push({
        type: 'ai',
        content,
        time: new Date()
      });
      
      this.scrollToBottom();
    },
    
    // 添加系统消息
    addSystemMessage(content) {
      this.conversation.push({
        type: 'system',
        content,
        time: new Date()
      });
      this.scrollToBottom();
    },
    
    // 清空对话
    clearConversation() {
      this.conversation = [];
      this.addSystemMessage('对话已清空');
    },
    
    // 格式化时间
    formatTime(date) {
      return new Date(date).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    },
    
    // 格式化回答内容
    formatAnswer(content) {
      // 这里可以添加简单的markdown渲染或其他格式化
      return content
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
    },
    

    
    // 滚动到底部
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.conversationHistory;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    }
  }
};
</script>

<style scoped>
.document-qa-container {
  width: 100%;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

h3 {
  margin-top: 0;
  color: #333;
  text-align: center;
}

.file-id-section {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: center;
}

.file-id-section label {
  white-space: nowrap;
  color: #666;
  font-weight: 500;
}

.file-id-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.check-status-btn {
  padding: 8px 16px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.check-status-btn:hover:not(:disabled) {
  background: #66b1ff;
}

.check-status-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.file-status-section {
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 20px;
  font-size: 14px;
}

.status-pending {
  background: #fdf6ec;
  border: 1px solid #faecd8;
  color: #e6a23c;
}

.status-processing {
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  color: #409eff;
}

.status-completed {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  color: #67c23a;
}

.status-partial {
  background: #fdf6ec;
  border: 1px solid #faecd8;
  color: #e6a23c;
}

.status-failed {
  background: #fef0f0;
  border: 1px solid #fde2e2;
  color: #f56c6c;
}

.file-status-section p {
  margin: 4px 0;
}

.qa-section {
  display: flex;
  flex-direction: column;
  height: 600px;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
  background: white;
}

.question-input-section {
  display: flex;
  padding: 15px;
  border-top: 1px solid #eee;
  gap: 10px;
}

.question-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.send-btn {
  padding: 8px 20px;
  background: #1989fa;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.send-btn:hover:not(:disabled) {
  background: #409eff;
}

.send-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.conversation-history {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 8px;
  word-wrap: break-word;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.user-message {
  align-self: flex-end;
  background: #1989fa;
  color: white;
}

.ai-message {
  align-self: flex-start;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #eee;
}

.system-message {
  align-self: center;
  background: #f0f9ff;
  color: #409eff;
  border: 1px solid #d9ecff;
  font-size: 12px;
  max-width: 90%;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  opacity: 0.8;
}

.user-message .message-header {
  color: rgba(255, 255, 255, 0.8);
}

.message-content {
  font-size: 14px;
  line-height: 1.6;
}

.sources {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #ddd;
  font-size: 12px;
}

.sources-title {
  margin-bottom: 5px;
  color: #666;
  font-weight: 500;
}

.source-item {
  background: #f9f9f9;
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 5px;
  border-left: 3px solid #409eff;
}

.source-text {
  margin-bottom: 4px;
  color: #333;
}

.source-meta {
  color: #999;
  font-size: 11px;
}

.typing-indicator {
  display: inline-block;
  padding: 4px 8px;
  background: #eee;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

.qa-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 10px 15px;
  border-top: 1px solid #eee;
  background: #fafafa;
}

.clear-btn,
.stop-btn {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.clear-btn {
  background: white;
  color: #666;
}

.clear-btn:hover {
  background: #f5f5f5;
}

.stop-btn {
  background: #f56c6c;
  color: white;
  border-color: #f56c6c;
}

.stop-btn:hover {
  background: #f78989;
}

.info-message,
.error-message {
  padding: 12px 16px;
  border-radius: 4px;
  margin-top: 15px;
}

.info-message {
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  color: #409eff;
}

.error-message {
  background: #fef0f0;
  border: 1px solid #fde2e2;
  color: #f56c6c;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .file-id-section {
    flex-direction: column;
    align-items: stretch;
  }
  
  .message {
    max-width: 90%;
  }
  
  .qa-section {
    height: 400px;
  }
  
  .document-qa-container {
    padding: 15px;
  }
}
</style>