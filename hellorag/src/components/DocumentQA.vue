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

          <div class="retrieval-scope">
            <span class="scope-label">
              检索范围
            </span>

          <button
            class="scope-btn"
            :class="{
              active:
              retrievalScope === 'current'
            }"
            @click="
              changeRetrievalScope('current')"
          >
            当前文档
          </button>

          <button
            class="scope-btn"
            :class="{
              active:
              retrievalScope === 'all'
            }"
           @click="
              changeRetrievalScope('all')
            "
          >
            全部文档
          </button>
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

      <!-- 操作按钮 -->
      <div class="qa-actions">
        <button @click="clearConversation" class="clear-btn">清空对话</button>
      </div>
  </div>

    
    <!-- 问答区域 -->
    <div class="qa-section" v-if="fileId">
      
      <!-- 对话历史 -->
    <div class="conversation-history" ref="conversationHistory"
    >
      <!-- 空对话状态 -->
    <div v-if="conversation.length === 0" class="conversation-empty"
    >
    <div class="empty-chat-icon">
      💬
    </div>

    <div class="empty-chat-title">
      开始基于文档提问
    </div>

    <div class="empty-chat-description">
      您可以询问文档内容、总结重点，
      或在全部文档中进行跨文档检索
    </div>
  </div>

  <!-- 对话消息 -->
  <div
    v-for="(message, index) in conversation"
    :key="index"
    class="message-wrapper"
  >
    <!-- 用户消息 -->
    <div
      v-if="message.type === 'user'"
      class="message user-message"
    >
      <div class="message-header">
        <span class="message-author">
          您
        </span>

        <span class="message-time">
          {{ formatTime(message.time) }}
        </span>
      </div>

      <div class="message-content">
        {{ message.content }}
      </div>
    </div>

    <!-- 系统消息 -->
    <div
      v-else-if="message.type === 'system'"
      class="message system-message"
    >
      <div class="message-header">
        <span class="message-author">
          系统
        </span>

        <span class="message-time">
          {{ formatTime(message.time) }}
        </span>
      </div>

      <div class="message-content">
        {{ message.content }}
      </div>
    </div>

    <!-- AI 消息 -->
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
        v-html="formatAnswer(message.content)"
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
        <div class="source-title-row">
          <div class="source-title">
            参考来源
          </div>

          <div class="source-scope-info">
            {{
              message.retrievalScope === 'all'
                ? `全部文档 · 命中 ${countSourceDocuments(message.sources)} 个文档`
                : '当前文档'
            }}
          </div>
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

      <!-- AI 操作 -->
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
            copiedMessageIndex === index
              ? '√ 已复制'
              : '复制'
          }}
        </button>
      </div>
    </div>
  </div>

  <!-- 等待第一块流式回答 -->
  <div
    v-if="
      isLoading &&
      !hasReceivedChunk
    "
    class="message ai-message typing"
  >
    <div class="message-header">
      <span class="message-author">
        AI助手
      </span>
    </div>

    <div class="message-content">
      <span class="typing-indicator">
        正在检索并生成回答...
      </span>
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
      
    
    <!-- 提示信息 -->
    <div v-if="!fileId" class="info-message">
      <p>请先选择或上传一个文档后开始问答</p>
    </div>
    
    <!-- 错误信息 -->
    <div v-if="error" class="error-message">
      <p>{{ error }}</p>
    </div>
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
    },

     retrievalScope: {
      type: String,
      default: 'current',

      validator(value) {
        return [
          'current',
          'all'
        ].includes(value);
      }
    }
  },

  emits: [
    'update:retrievalScope'
  ],

  data() {
    return {
      question: '',
      conversation: [],
      error: null,
      isLoading: false,
      // 是否已经收到第一块流式回答
      hasReceivedChunk: false,
      // 需要知道具体是那一条回答被选中复制，因而需要用index来标记
      copiedMessageIndex: null,
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
     this.addAIMessage('',[],this.retrievalScope);

      const aiMessageIndex =
        this.conversation.length - 1;

     try {
      const targetDocumentId =
        this.retrievalScope === 'current'
          ? this.fileId
         : null;
       await apiService
          .askQuestionStream(
            targetDocumentId,
            questionText,

            (chunk, fullText) => {
              this.hasReceivedChunk = true;
            
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
      sources = [],
      retrievalScope = 'current'
    ) {
      this.conversation.push({
        type: 'ai',
        content,
        sources,
        retrievalScope,
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

      this.error = null;

      this.isLoading = false;

      this.hasReceivedChunk = false;

      this.copiedMessageIndex = null;
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
    },

    changeRetrievalScope(scope) {
      this.$emit('update:retrievalScope',scope);
    },

    countSourceDocuments(sources = []) {
      const fileNames = sources.map(source => source.file_name).filter(Boolean);

      return new Set(
        fileNames
      ).size;
    },
  }
};
</script>

<style scoped src="../styles/document-qa.css">
</style>