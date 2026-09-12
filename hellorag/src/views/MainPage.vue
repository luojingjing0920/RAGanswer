<template>
  <div class="main-container" :class="{'qa-page': currentStep === 'qa'}">
    <!-- 顶部导航栏 -->
    <header class="navbar">
      <div class="navbar-container">
        <div class="logo">
          <h1>RAG智能文档问答系统</h1>
        </div>
        <div class="navbar-actions">
          <button @click="showAbout = true" class="about-btn">关于</button>
        </div>
      </div>
    </header>

    <!-- 主要内容区域 -->
    <main class="content" :class="{
      'init-mode': currentStep === 'init',
      'upload-mode': currentStep === 'upload',
      'qa-mode': currentStep === 'qa'
    }">
    <!-- 侧边栏 -->
      <aside class="sidebar">
        <!-- 文档列表区域 -->
        <div v-if="uploadedFiles.length > 0" class="files-section">
          <div>
            <h3>我的文档</h3>
            <p>{{ uploadedFiles.length }} 个文档</p>
          </div>
          <button
            class="new-file-btn"
            @click="startUpload"
          >
            + 上传
          </button>
          <div class="files-list">
            <div
              v-for="file in uploadedFiles"
              :key="file.id"
              class="file-item"
              :class="{
                active:
                retrievalScope === 'current' &&
                file.id === uploadedFileId,

              'in-scope':
                retrievalScope === 'all',
             }"
              @click="selectFile(file.id)"
            >
              <div class="file-info">
                <div class="file-main">
                  <span class="file-icon">📄</span>
                  <div class="file-meta">
                    <div class="file-name">{{ file.name || `文件 ${file.id.substring(0, 8)}...` }}</div>
                    <div class="file-time">{{ formatDate(file.time) }}</div>
                  </div>
                </div>
              </div>
              <div class="file-actions">
                <button
                  @click.stop="removeFile(file.id)"
                  class="remove-btn"
                  title="删除文档记录"
                >
                  ×
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 空状态提示 -->
        <div v-else class="empty-state">
          <div class="empty-icon">📄</div>
          <p>暂无历史文档</p>
          <p class="empty-hint">上传文档后将在此显示</p>
        </div>
      </aside>
      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 状态提示 -->
        <div v-if="currentStep === 'init'" class="welcome-section">
          <div class="welcome-card">
            <div class="welcome-icon">📚</div>
            <h2>欢迎使用RAG智能文档问答系统</h2>
            <p>上传您的文档，然后开始提问，系统将基于文档内容为您提供精准回答。</p>
            <button @click="startUpload" class="start-btn">开始使用</button>
          </div>
        </div>

        <!-- 文档上传区域 -->
        <div v-if="currentStep === 'upload'" class="upload-section">
          <FileUpload @file-uploaded="handleFileUploaded" />
        </div>

        <!-- 文档问答区域 -->
        <div v-if="currentStep === 'qa'" class="qa-section">
          <DocumentQA 
            :key="uploadedFileId" :initial-file-id="uploadedFileId" :file-name="currentFileName"
            v-model:retrieval-scope="retrievalScope"
          />
        </div>
      </div>
    </main>

    <!-- 底部信息 -->
    <footer  v-if="currentStep !== 'qa'" class="footer">
      <div class="footer-content">
        <p>© 2026 RAG智能文档问答系统 · Self-built Retrieval Pipeline</p>
      </div>
    </footer>

    <!-- 关于对话框 -->
    <div v-if="showAbout" class="modal-overlay" @click="showAbout = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>关于系统</h3>
          <button @click="showAbout = false" class="close-btn">&times;</button>
        </div>
        <div class="modal-content">
          <p><strong>RAG智能文档问答系统</strong></p>
          <p>基于文档解析、重叠切块、
             多语言 Embedding、
             ChromaDB 向量检索和
             大语言模型生成构建的
             RAG 文档问答系统。
          </p>
          <h4>功能特点：</h4>
          <ul>
            <li>支持多种文档格式上传（docx、pdf、md、txt）
                文档上传与索引
            </li>
            <li>基于 Top-K 语义检索获取
                相关文档片段
            </li>
            <li>使用相似度阈值过滤
                低相关内容
            </li>
            <li>支持 AI 回答流式输出
                与参考来源追踪
            </li>
            <li>支持本地文件和URL上传</li>
          </ul>
          <h4>使用说明：</h4>
          <ol>
            <li>上传您的文档文件</li>
            <li>等待文档处理完成</li>
            <li>输入您的问题并获取答案</li>
          </ol>
        </div>
      </div>
    </div>

    <!-- 提示消息 -->
    <div v-if="message" class="message-toast" :class="messageType">
      {{ message }}
    </div>
  </div>
</template>

<script>
import FileUpload from '../components/FileUpload.vue';
import DocumentQA from '../components/DocumentQA.vue';
import apiService from '../services/apiService';

export default {
  name: 'MainPage',
  components: {
    FileUpload,
    DocumentQA
  },
  data() {
    return {
      currentStep: 'init', // 'init', 'upload', 'qa'
      uploadedFileId: '',
      uploadedFiles: [],
      showAbout: false,
      message: '',
      messageType: 'info', // 'info', 'success', 'error', 'warning'
      retrievalScope: 'current'
    };
  },

  computed: {
    // 当前正在使用的文档
    currentFile() {
      return (
        this.uploadedFiles.find(
          file => file.id === this.uploadedFileId
        ) || null
      );
    },

    // 当前文档显示名称
    currentFileName() {
      return this.currentFile?.name || '当前文档';
    }
  },

  mounted() {
    // 从localStorage加载历史文件
    this.loadHistoryFiles();
    
    // 检查是否有未完成的上传
    const lastFileId = localStorage.getItem('lastRagDocumentId');
    if (lastFileId) {
      this.uploadedFileId = lastFileId;
      this.currentStep = 'qa';
    }
  },
  methods: {
    // 开始上传
    startUpload() {
      this.currentStep = 'upload';
    },
    
    // 处理文件上传完成
    handleFileUploaded(fileId, fileName) {
      this.uploadedFileId = fileId;
 
      // 新上传文档后，默认针对该文档问答
      this.retrievalScope = 'current';

      // 保存文件 ID + 文件名
      this.addToHistory(fileId, fileName);

      // 保存最后使用的文件ID
      localStorage.setItem('lastRagDocumentId', fileId);

      // 切换到问答页面
      this.currentStep = 'qa';

      this.showMessage(
        '文件上传成功，正在跳转至问答界面...',
        'success'
      );
    },
    
    // 选择历史文件
    selectFile(fileId) {
      this.uploadedFileId = fileId;
      this.currentStep = 'qa';
      localStorage.setItem('lastRagDocumentId', fileId);
      this.showMessage('已切换到选中的文档', 'info');
    },
    
    // 从历史记录中移除文件
    async removeFile(fileId) {
      const confirmed = confirm(
        '确定要删除这个文档吗？删除后将同时移除该文档的向量索引。'
      );
        
      if (!confirmed) {
        return;
      }
    
      try {
        /**
         * 先删除后端向量。
         *
         * 后端成功后，
         * 再删除前端 LocalStorage。
         */
        await apiService.deleteDocument(
          fileId
        );
      
        this.uploadedFiles =
          this.uploadedFiles.filter(
            file => file.id !== fileId
          );
      
        localStorage.setItem(
          'ragUploadedFiles',
          JSON.stringify(
            this.uploadedFiles
          )
        );
      
        if (
          this.uploadedFileId === fileId
        ) {
          this.uploadedFileId = '';
        
          localStorage.removeItem(
            'lastRagDocumentId'
          );
        
          if (
            this.uploadedFiles.length > 0
          ) {
            const nextFile =
              this.uploadedFiles[0];
          
            this.uploadedFileId =
              nextFile.id;
          
            localStorage.setItem(
              'lastRagDocumentId',
              nextFile.id
            );
          
            this.currentStep = 'qa';
          
          } else {
            this.currentStep = 'init';
          }
        }
      
        this.showMessage(
          '文档及向量索引已删除',
          'success'
        );
      
      } catch (error) {
        console.error(
          '删除文档失败:',
          error
        );
      
        this.showMessage(
          error.message ||
          '删除文档失败',
          'error'
        );
      }
    },
    
    // 添加到历史记录
    addToHistory(fileId, fileName) {
      const exists = this.uploadedFiles.some(
        file => file.id === fileId
      );

      if (!exists) {
        const newFile = {
          id: fileId,
          name: fileName,
          time: new Date().toISOString()
        };

        this.uploadedFiles.unshift(newFile);

        if (this.uploadedFiles.length > 10) {
          this.uploadedFiles =
            this.uploadedFiles.slice(0, 10);
        }

        localStorage.setItem(
          'ragUploadedFiles',
          JSON.stringify(this.uploadedFiles)
        );
      }
    },
    
    // 加载历史文件
    loadHistoryFiles() {
      try {
        const stored = localStorage.getItem('ragUploadedFiles');
        if (stored) {
          this.uploadedFiles = JSON.parse(stored);
        }
      } catch (error) {
        console.error('加载历史文件失败:', error);
      }
    },
    
    // 格式化日期
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    },
    
    // 显示消息提示
    showMessage(text, type = 'info') {
      this.message = text;
      this.messageType = type;
      
      // 3秒后自动隐藏
      setTimeout(() => {
        this.message = '';
      }, 3000);
    }
  }
};
</script>

<style scoped src="../styles/main.css">
</style>