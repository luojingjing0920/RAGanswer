<template>
  <div class="main-container">
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
      'upload-mode': currentStep === 'upload'
    }">
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
          <DocumentQA :initial-file-id="uploadedFileId" />
        </div>
      </div>

      <!-- 侧边栏 -->
      <aside class="sidebar">
        <!-- 文档列表区域 -->
        <div v-if="uploadedFiles.length > 0" class="files-section">
          <h3>历史文档</h3>
          <div class="files-list">
            <div 
              v-for="file in uploadedFiles" 
              :key="file.id"
              class="file-item"
              @click="selectFile(file.id)"
            >
              <div class="file-info">
                <div class="file-name">{{ file.name || `文件 ${file.id.substring(0, 8)}...` }}</div>
                <div class="file-time">{{ formatDate(file.time) }}</div>
              </div>
              <div class="file-actions">
                <button @click.stop="selectFile(file.id)" class="use-btn">使用</button>
                <button @click.stop="removeFile(file.id)" class="remove-btn">删除</button>
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
    </main>

    <!-- 底部信息 -->
    <footer class="footer">
      <div class="footer-content">
        <p>© 2024 RAG智能文档问答系统 - 基于讯飞星火大模型</p>
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
          <p>这是一个基于检索增强生成（RAG）技术的智能文档问答原型系统，使用讯飞星火大模型提供强大的问答能力。</p>
          <h4>功能特点：</h4>
          <ul>
            <li>支持多种文档格式上传（doc/docx、pdf、md、txt）</li>
            <li>基于文档内容进行精准问答</li>
            <li>显示回答的参考来源</li>
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
      messageType: 'info' // 'info', 'success', 'error', 'warning'
    };
  },
  mounted() {
    // 从localStorage加载历史文件
    this.loadHistoryFiles();
    
    // 检查是否有未完成的上传
    const lastFileId = localStorage.getItem('lastFileId');
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
    handleFileUploaded(fileId) {
      this.uploadedFileId = fileId;
      
      // 保存到历史记录
      this.addToHistory(fileId);
      
      // 保存最后使用的文件ID
      localStorage.setItem('lastFileId', fileId);
      
      // 切换到问答步骤
      this.currentStep = 'qa';
      
      // 显示成功消息
      this.showMessage('文件上传成功，正在跳转至问答界面...', 'success');
    },
    
    // 选择历史文件
    selectFile(fileId) {
      this.uploadedFileId = fileId;
      this.currentStep = 'qa';
      localStorage.setItem('lastFileId', fileId);
      this.showMessage('已切换到选中的文档', 'info');
    },
    
    // 从历史记录中移除文件
    removeFile(fileId) {
      if (confirm('确定要删除这个文档记录吗？')) {
        this.uploadedFiles = this.uploadedFiles.filter(file => file.id !== fileId);
        localStorage.setItem('uploadedFiles', JSON.stringify(this.uploadedFiles));
        
        // 如果删除的是当前使用的文件，重置状态
        if (this.uploadedFileId === fileId) {
          this.uploadedFileId = '';
          this.currentStep = 'init';
          localStorage.removeItem('lastFileId');
        }
        
        this.showMessage('文档记录已删除', 'info');
      }
    },
    
    // 添加到历史记录
    addToHistory(fileId) {
      // 检查是否已存在
      const exists = this.uploadedFiles.some(file => file.id === fileId);
      if (!exists) {
        const newFile = {
          id: fileId,
          time: new Date()
        };
        
        this.uploadedFiles.unshift(newFile);
        
        // 限制历史记录数量
        if (this.uploadedFiles.length > 10) {
          this.uploadedFiles = this.uploadedFiles.slice(0, 10);
        }
        
        // 保存到localStorage
        localStorage.setItem('uploadedFiles', JSON.stringify(this.uploadedFiles));
      }
    },
    
    // 加载历史文件
    loadHistoryFiles() {
      try {
        const stored = localStorage.getItem('uploadedFiles');
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

<style scoped>
.main-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 导航栏样式 */
.navbar {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 15px 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo h1 {
  margin: 0;
  font-size: 28px;
  color: #333;
  font-weight: 600;
}

.about-btn {
  padding: 10px 20px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s ease;
}

.about-btn:hover {
  background: #66b1ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

/* 主要内容样式 */
.content {
  flex: 1;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem;
  display: flex;
  flex-direction: row;
  gap: 2rem;
}

/* 主内容区和侧边栏布局 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.sidebar {
  width: 320px;
  flex-shrink: 0;
}

/* 在初始化或上传阶段使用单列布局 */
.content.init-mode,
.content.upload-mode {
  flex-direction: column;
}

.content.init-mode .main-content,
.content.upload-mode .main-content {
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.content.init-mode .sidebar,
.content.upload-mode .sidebar {
  display: none;
}

/* 欢迎区域样式 */
.welcome-section {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.welcome-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  transform: translateY(-20px);
  animation: slideUp 0.6s ease-out forwards;
}

@keyframes slideUp {
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.welcome-card h2 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 28px;
}

.welcome-card p {
  color: #666;
  line-height: 1.6;
  margin-bottom: 30px;
  font-size: 16px;
}

.start-btn {
  padding: 12px 36px;
  background: linear-gradient(45deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 30px;
  font-size: 18px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

/* 上传和问答区域样式 */
.upload-section,
.qa-section {
  background: white;
  border-radius: 12px;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 文档列表样式 */
.files-section {
  background: white;
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
  height: fit-content;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

/* 空状态样式 */
.empty-state {
  background: white;
  border-radius: 12px;
  padding: 40px 25px;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
  text-align: center;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 15px;
  opacity: 0.5;
}

.empty-hint {
  font-size: 14px;
  color: #ccc;
  margin-top: 5px;
}

.files-section h3 {
  margin-top: 0;
  color: #333;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 10px;
  margin-bottom: 20px;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: #f9f9f9;
  border-radius: 8px;
  transition: all 0.3s;
  cursor: pointer;
  border: 1px solid transparent;
}

.file-item:hover {
  background: #f0f0f0;
  border-color: #409eff;
  transform: translateX(5px);
}

.file-info {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: #333;
  margin-bottom: 5px;
}

.file-time {
  font-size: 12px;
  color: #999;
}

.file-actions {
  display: flex;
  gap: 8px;
}

.use-btn,
.remove-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.3s;
}

.use-btn {
  background: #409eff;
  color: white;
}

.use-btn:hover {
  background: #66b1ff;
}

.remove-btn {
  background: #f56c6c;
  color: white;
}

.remove-btn:hover {
  background: #f78989;
}

/* 底部样式 */
.footer {
  background: rgba(0, 0, 0, 0.1);
  padding: 20px 0;
  margin-top: auto;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease-out;
}

.modal {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-50px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.3s;
}

.close-btn:hover {
  background: #f0f0f0;
  color: #333;
}

.modal-content {
  padding: 25px;
  line-height: 1.6;
  color: #666;
}

.modal-content h4 {
  margin-top: 20px;
  margin-bottom: 10px;
  color: #333;
}

.modal-content ul,
.modal-content ol {
  margin: 10px 0;
  padding-left: 25px;
}

.modal-content li {
  margin-bottom: 8px;
}

/* 消息提示样式 */
.message-toast {
  position: fixed;
  top: 80px;
  right: 20px;
  padding: 12px 20px;
  border-radius: 4px;
  color: white;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: slideInRight 0.3s ease-out;
  z-index: 1001;
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.message-toast.info {
  background: #409eff;
}

.message-toast.success {
  background: #67c23a;
}

.message-toast.error {
  background: #f56c6c;
}

.message-toast.warning {
  background: #e6a23c;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .navbar-container {
    padding: 0 15px;
  }
  
  .logo h1 {
    font-size: 20px;
  }
  
  .content {
    padding: 20px 15px;
    gap: 20px;
  }
  
  .welcome-card {
    padding: 30px 20px;
  }
  
  .welcome-card h2 {
    font-size: 24px;
  }
  
  .file-item {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  
  .file-actions {
    justify-content: flex-end;
  }
  
  .message-toast {
    right: 10px;
    left: 10px;
    text-align: center;
  }
}
</style>