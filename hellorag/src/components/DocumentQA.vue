<template>
  <div class="document-qa-container">
  
    <div class="qa-header">
      <div class="current-document">
        <div class="document-icon">
          📄
        </div>

        <div class="document-info">
          <div class="document-label">
            当前文档
          </div>

          <div class="document-name">
            {{ fileName }}
          </div>
        </div>
      </div>

      <div class="document-status">
        <span class="status-dot"></span>
        已就绪
      </div>
    </div>
    
    <!-- 问答区域 -->
    <div class="qa-section" v-if="fileId">
      
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
        <div
          v-else-if="message.type === 'ai'"
          class="message ai-message"
>
  <div class="message-header">
    <span class="message-author">
      AI助手
    </span>

    <span class="message-time">
      {{ formatTime(message.time) }}
    </span>
  </div>

  <!-- Markdown 回答 -->
  <div
    class="message-content markdown-body"
    v-html="
      formatAnswer(message.content)
    "
  ></div>

  <!-- RAG 来源 -->
  <div
    v-if="
      message.content &&
      message.sources &&
      message.sources.length
    "
    class="source-list"
  >
    <div class="source-title">
      参考来源
    </div>

    <details
      v-for="source in message.sources"
              :key="
                `${source.source_id}-${source.chunk_index}`
             "
              class="source-card"
            >
              <summary>
                <span class="source-index">
                  [{{ source.source_id }}]
               </span>

                <span class="source-file">
                  {{ source.file_name }}
                </span>

               <span class="source-location">
                 {{
                   formatSourceLocation(
                      source
                    )
                 }}
                </span>
              </summary>

              <div class="source-meta">
                语义相关度：
                {{
                  formatSimilarity(
                   source.similarity
                  )
                }}
              </div>

              <div class="source-text">
                {{ source.text }}
              </div>
            </details>
          </div>

          <div
            v-if="message.content"
           class="message-actions"
          >
            <button
              class="copy-btn"
              @click="
                copyAnswer(
                 message.content,
                  index
               )
              "
            >
              {{
                copiedMessageIndex ===
                index
                  ? '√已复制'
                 : '复制'
              }}
            </button>
          </div>
        </div>
    </div>
        
        <!-- 正在输入提示 -->
        <div v-if="isLoading && !hasReceivedChunk" class="message ai-message typing">
          <div class="message-header">
            <span class="message-author">AI助手</span>
          </div>
          <div class="message-content">
            <span class="typing-indicator">正在生成回答...</span>
          </div>
        </div>
      </div>

      <!-- 问题输入 -->
      <div class="question-input-section">
        <textarea 
          v-model="question" 
          rows="1"
          placeholder="请输入您的问题..."
          class="question-input"
          :disabled="isLoading"
          @keydown="handleQuestionKeydown"
        ></textarea>
        <button 
          @click="sendQuestion"
          :disabled="!canSendQuestion || isLoading"
          class="send-btn"
          title="发送"
        >
          {{ isLoading ? '...' : '⬆️' }}
        </button>
      </div>
      
      <!-- 操作按钮 -->
      <div class="qa-actions">
        <button @click="clearConversation" class="clear-btn">清空对话</button>
      </div>
    </div>
    
    <!-- 提示信息 -->
    <div v-if="!fileId" class="info-message">
      <p>请先选择或上传一个文档后开始问答</p>
    </div>
    
    <!-- 错误信息 -->
    <div v-if="error" class="error-message">
      <p>{{ error }}</p>
    </div>
  </div>
</template>

<script>
import apiService from '../services/apiService';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export default {
  name: 'DocumentQA',
  props: {
    // 可以从父组件传入文件ID
    initialFileId: {
      type: String,
      default: ''
    },

    fileName: {
    type: String,
    default: '当前文档'
  }
  },
  data() {
    return {
      question: '',
      conversation: [],
      error: null,
      isLoading: false,
      // 是否已经收到第一块流式回答
      hasReceivedChunk: false,
      // 需要知道具体是那一条回答被选中复制，因而需要用index来标记
      copiedMessageIndex: null
    };
  },
  computed: {
    fileId() {
      return this.initialFileId;
    },

    canSendQuestion() {
      return this.question.trim() && !this.isLoading;
    }
  },
  methods: {
    handleQuestionKeydown(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        this.sendQuestion();
      }
    },

    // 发送问题
    async sendQuestion() {
      if (!this.canSendQuestion) {
        return;
      }

      const questionText =
        this.question.trim();

      this.addUserMessage(
        questionText
      );

     this.question = '';
     this.isLoading = true;
     this.hasReceivedChunk = false;
     this.error = null;

     /**
      * 先创建空 AI Message。
      *
      * 后面 answer 和 sources
      * 都更新这一条。
      */
     this.addAIMessage('');

      const aiMessageIndex =
        this.conversation.length - 1;

     try {
       await apiService
          .askQuestionStream(
           this.fileId,
            questionText,

            /**
             * answer 事件
             */
            (chunk, fullText) => {
              this.hasReceivedChunk =
                true;
            
             const message =
               this.conversation[
                 aiMessageIndex
               ];

             if (!message) {
               return;
             }

             message.content =
               fullText;

             this.scrollToBottom();
            },

            /**
             * sources 事件
             */
            (sources) => {
              const message =
                this.conversation[
                  aiMessageIndex
                ];
            
              if (!message) {
                return;
              }

              message.sources =
                sources;

              this.scrollToBottom();
            }
          );

      } catch (err) {
        console.error(
          'RAG 问答错误:',
          err
        );

        this.error =
          err.message ||
          '问答失败，请稍后重试';

        const message =
          this.conversation[
            aiMessageIndex
          ];

        if (
          message &&
          !message.content
        ) {
          this.conversation.splice(
            aiMessageIndex,
            1
          );
        }

        this.addSystemMessage(
          `错误: ${this.error}`
        );

      } finally {
       this.isLoading = false;

       this.hasReceivedChunk =
         false;
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
    addAIMessage(
      content,
      sources = []
    ) {
      this.conversation.push({
        type: 'ai',
        content,
        sources,
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
    
    formatSourceLocation(
      source
    ) {
      if (
        source.page !== null &&
        source.page !== undefined
      ) {
        return `第 ${source.page} 页`;
      }

      if (
        source.chunk_index !==
          null &&
        source.chunk_index !==
          undefined
      ) {
        return `片段 ${
          source.chunk_index + 1
        }`;
      }

      return '文档片段';
    },

    formatSimilarity(
      similarity
    ) {
      if (
        typeof similarity !==
        'number'
      ) {
        return '-';
      }

      return `${
        (
         similarity * 100
        ).toFixed(1)
      }%`;
    },

    // 格式化回答内容
    formatAnswer(content) {
      if (!content) return '';

      const html = marked.parse(content, {
        breaks: true,
        gfm: true
      });

      return DOMPurify.sanitize(html);
    },

    // 复制回答内容
    async copyAnswer(content, index) {
      if (!content) return;

      try {
        await navigator.clipboard.writeText(content);

        this.copiedMessageIndex = index;

        setTimeout(() => {
          if (this.copiedMessageIndex === index) {
            this.copiedMessageIndex = null;
          }
        }, 1500);
      } catch (error) {
        console.error('复制回答失败:', error);
        this.error = '复制失败，请手动复制回答内容';
      }
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

.qa-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 4px 18px;
  border-bottom: 1px solid #edf0f5;
  margin-bottom: 16px;
}

.current-document {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.document-icon {
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 10px;
  background: #eef4ff;
  font-size: 20px;
}

.document-info {
  min-width: 0;
}

.document-label {
  margin-bottom: 2px;
  font-size: 12px;
  color: #909399;
}

.document-name {
  max-width: 420px;
  overflow: hidden;
  color: #303133;
  font-size: 15px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-status {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding: 5px 10px;
  border-radius: 999px;
  background: #f0f9eb;
  color: #67c23a;
  font-size: 12px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
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
  align-items: flex-end;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid #ebeef5;
  background: white;
}

.question-input {
  flex: 1;

  min-height: 44px;
  max-height: 120px;

  padding: 11px 14px;

  border: 1px solid #dcdfe6;
  border-radius: 12px;

  font-family: inherit;
  font-size: 14px;
  line-height: 20px;

  resize: none;
  outline: none;

  transition: border-color 0.2s,
              box-shadow 0.2s;
}

.question-input:focus {
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
}

.send-btn {
  width: 44px;
  height: 44px;
  flex-shrink: 0;

  padding: 0;

  border: none;
  border-radius: 12px;

  background: #409eff;
  color: white;

  font-size: 22px;
  cursor: pointer;
}

.send-btn:hover:not(:disabled) {
  background: #337ecc;
}

.send-btn:disabled {
  background: #dcdfe6;
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

.message-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
}

.copy-btn {
  padding: 4px 8px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #909399;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: #eef4ff;
  color: #409eff;
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

/* AI Markdown 内容 */
.markdown-body {
  line-height: 1.75;
  word-break: break-word;
}

/* 标题 */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 16px 0 10px;
  line-height: 1.4;
  color: #222;
}

.markdown-body :deep(h1) {
  font-size: 20px;
}

.markdown-body :deep(h2) {
  font-size: 18px;
}

.markdown-body :deep(h3) {
  font-size: 16px;
}

/* 第一行标题不要留太大顶部空白 */
.markdown-body :deep(h1:first-child),
.markdown-body :deep(h2:first-child),
.markdown-body :deep(h3:first-child) {
  margin-top: 0;
}

/* 普通段落 */
.markdown-body :deep(p) {
  margin: 8px 0;
}

/* 列表 */
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 22px;
  margin: 8px 0;
}

.markdown-body :deep(li) {
  margin: 4px 0;
}

/* 引用 */
.markdown-body :deep(blockquote) {
  margin: 10px 0;
  padding: 8px 12px;
  border-left: 4px solid #409eff;
  background: #f5f7fa;
  color: #606266;
}

/* 行内代码 */
.markdown-body :deep(code) {
  padding: 2px 5px;
  border-radius: 4px;
  background: #eef0f3;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
}

/* 代码块 */
.markdown-body :deep(pre) {
  overflow-x: auto;
  padding: 12px;
  margin: 10px 0;
  border-radius: 6px;
  background: #282c34;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
  color: #abb2bf;
}

/* 分割线 */
.markdown-body :deep(hr) {
  margin: 16px 0;
  border: none;
  border-top: 1px solid #e5e7eb;
}

.source-list {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}

.source-title {
  margin-bottom: 8px;
  color: #606266;
  font-size: 13px;
  font-weight: 600;
}

.source-card {
  margin-bottom: 8px;
  padding: 0;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

.source-card summary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  cursor: pointer;
  list-style: none;
  font-size: 12px;
}

.source-card summary::-webkit-details-marker {
  display: none;
}

.source-card summary::after {
  content: '⌄';
  margin-left: 4px;
  color: #909399;
}

.source-card[open]
summary::after {
  content: '⌃';
}

.source-index {
  flex-shrink: 0;
  color: #409eff;
  font-weight: 600;
}

.source-file {
  min-width: 0;
  overflow: hidden;
  color: #303133;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-location {
  flex-shrink: 0;
  margin-left: auto;
  color: #909399;
}

.source-meta {
  padding: 8px 10px 0;
  border-top: 1px solid #f0f2f5;
  color: #909399;
  font-size: 11px;
}

.source-text {
  max-height: 160px;
  overflow-y: auto;
  padding: 8px 10px 10px;
  color: #606266;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
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