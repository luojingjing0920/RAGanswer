<template>
  <div
    class="main-container"
    :class="{
      'qa-page': currentStep === 'qa'
    }"
  >
    <!-- 顶部导航栏 -->
    <header class="navbar">
      <div class="navbar-container">
        <div class="logo">
          <h1>RAG智能文档问答系统</h1>
        </div>

        <div class="navbar-actions">
          <button
            class="about-btn"
            @click="showAbout = true"
          >
            关于
          </button>
        </div>
      </div>
    </header>

    <!-- 主要内容区域 -->
    <main
      class="content"
      :class="{
        'init-mode':
          currentStep === 'init',

        'upload-mode':
          currentStep === 'upload',

        'qa-mode':
          currentStep === 'qa'
      }"
    >
      <!-- 侧边栏 -->
      <aside class="sidebar">
        <!-- 文档列表 -->
        <div
          v-if="uploadedFiles.length > 0"
          class="files-section"
        >
          <div>
            <h3>我的文档</h3>

            <p>
              {{ uploadedFiles.length }}
              个文档
            </p>
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
                  retrievalScope === 'all'
              }"
              @click="selectFile(file.id)"
            >
              <div class="file-info">
                <div class="file-main">
                  <span class="file-icon">
                    📄
                  </span>

                  <div class="file-meta">
                    <div
                      class="file-name"
                      :title="file.name"
                    >
                      {{
                        file.name ||
                        `文件 ${file.id.substring(
                          0,
                          8
                        )}...`
                      }}
                    </div>

                    <div class="file-time">
                      {{
                        formatDate(
                          file.time
                        )
                      }}
                    </div>
                  </div>
                </div>
              </div>

              <div class="file-actions">
                <button
                  class="remove-btn"
                  title="删除文档"
                  @click.stop="
                    removeFile(
                      file.id
                    )
                  "
                >
                  ×
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div
          v-else
          class="empty-state"
        >
          <div class="empty-icon">
            📄
          </div>

          <p>
            暂无文档
          </p>

          <p class="empty-hint">
            上传文档后将在此显示
          </p>
        </div>
      </aside>

      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 欢迎页 -->
        <div
          v-if="currentStep === 'init'"
          class="welcome-section"
        >
          <div class="welcome-card">
            <div class="welcome-icon">
              📚
            </div>

            <h2>
              欢迎使用RAG智能文档问答系统
            </h2>

            <p>
              上传您的文档，然后开始提问，
              系统将基于文档内容为您提供回答。
            </p>

            <button
              class="start-btn"
              @click="startUpload"
            >
              开始使用
            </button>
          </div>
        </div>

        <!-- 文档上传 -->
        <div
          v-if="currentStep === 'upload'"
          class="upload-section"
        >
          <FileUpload
            @file-uploaded="
              handleFileUploaded
            "
          />
        </div>

        <!-- 文档问答 -->
        <div
          v-if="currentStep === 'qa'"
          class="qa-section"
        >
          <DocumentQA
            :key="uploadedFileId"
            :initial-file-id="
              uploadedFileId
            "
            :file-name="
              currentFileName
            "
            v-model:retrieval-scope="
              retrievalScope
            "
          />
        </div>
      </div>
    </main>

    <!-- 底部信息 -->
    <footer
      v-if="currentStep !== 'qa'"
      class="footer"
    >
      <div class="footer-content">
        <p>
          © 2026 RAG智能文档问答系统
          · Self-built Retrieval Pipeline
        </p>
      </div>
    </footer>

    <!-- 关于 -->
    <div
      v-if="showAbout"
      class="modal-overlay"
      @click="showAbout = false"
    >
      <div
        class="modal"
        @click.stop
      >
        <div class="modal-header">
          <h3>
            关于系统
          </h3>

          <button
            class="close-btn"
            @click="
              showAbout = false
            "
          >
            &times;
          </button>
        </div>

        <div class="modal-content">
          <p>
            <strong>
              RAG智能文档问答系统
            </strong>
          </p>

          <p>
            基于文档解析、重叠切块、
            多语言 Embedding、
            ChromaDB 向量检索和
            大语言模型生成构建的
            RAG 文档问答系统。
          </p>

          <h4>
            功能特点：
          </h4>

          <ul>
            <li>
              支持 PDF、DOCX、MD、TXT
              文档上传与索引
            </li>

            <li>
              基于 Top-K 语义检索获取
              相关文档片段
            </li>

            <li>
              使用相似度阈值过滤
              低相关内容
            </li>

            <li>
              支持当前文档与全部文档
              两种检索范围
            </li>

            <li>
              支持 AI 回答流式输出
              与参考来源追踪
            </li>
          </ul>

          <h4>
            使用说明：
          </h4>

          <ol>
            <li>
              上传您的文档文件
            </li>

            <li>
              等待文档解析与向量索引完成
            </li>

            <li>
              选择检索范围
            </li>

            <li>
              输入问题并获取回答
            </li>
          </ol>
        </div>
      </div>
    </div>

    <!-- 提示消息 -->
    <div
      v-if="message"
      class="message-toast"
      :class="messageType"
    >
      {{ message }}
    </div>
  </div>
</template>

<script>
import FileUpload
  from '../components/FileUpload.vue';

import DocumentQA
  from '../components/DocumentQA.vue';

import apiService
  from '../services/apiService';


export default {
  name: 'MainPage',

  components: {
    FileUpload,
    DocumentQA
  },


  data() {
    return {
      // 当前页面状态：
      // init / upload / qa
      currentStep: 'init',

      // 当前选中文档 ID
      uploadedFileId: '',

      // 文档列表
      // 数据来源改为后端 ChromaDB
      uploadedFiles: [],

      // 当前检索范围
      // current / all
      retrievalScope: 'current',

      showAbout: false,

      message: '',

      messageType: 'info'
    };
  },


  computed: {
    /**
     * 当前正在查看的文档。
     */
    currentFile() {
      return (
        this.uploadedFiles.find(
          (file) =>
            file.id ===
            this.uploadedFileId
        ) || null
      );
    },


    /**
     * 当前文档显示名称。
     */
    currentFileName() {
      return (
        this.currentFile?.name ||
        '当前文档'
      );
    }
  },


  async mounted() {
    /**
     * 页面启动时不再从
     * LocalStorage 恢复文档列表。
     *
     * 文档真实状态统一从
     * ChromaDB / FastAPI 获取。
     */
    await this.refreshDocuments();

    if (this.uploadedFileId) {
      this.currentStep = 'qa';
    } else {
      this.currentStep = 'init';
    }
  },


  methods: {
    /**
     * 进入上传页面。
     */
    startUpload() {
      this.currentStep =
        'upload';
    },


    /**
     * 上传完成。
     *
     * FileUpload 上传成功后
     * 会返回新文档 document_id。
     *
     * 上传后重新从后端同步
     * 文档列表，而不是手动
     * 往 LocalStorage 中插入数据。
     */
    async handleFileUploaded(
      fileId
    ) {
      this.uploadedFileId =
        fileId;

      /**
       * 新上传文档默认进入
       * “当前文档”检索模式。
       */
      this.retrievalScope =
        'current';

      /**
       * 仅保存最后选中的 ID。
       *
       * LocalStorage 不再保存
       * 文档列表。
       */
      localStorage.setItem(
        'lastRagDocumentId',
        fileId
      );

      /**
       * 从 ChromaDB 重新同步
       * 真实文档列表。
       */
      await this.refreshDocuments();

      /**
       * 进入问答页面。
       */
      this.currentStep = 'qa';

      this.showMessage(
        '文件上传成功，可以开始提问',
        'success'
      );
    },


    /**
     * 选择左侧文档。
     */
    selectFile(fileId) {
      this.uploadedFileId =
        fileId;

      this.currentStep = 'qa';

      /**
       * 这里保存的是
       * “用户最后选择的文档”，
       * 不是知识库文档列表。
       */
      localStorage.setItem(
        'lastRagDocumentId',
        fileId
      );
    },


    /**
     * 删除文档。
     *
     * 删除顺序：
     *
     * FastAPI
     *   ↓
     * ChromaDB 删除
     *   ↓
     * refreshDocuments()
     *   ↓
     * 前端重新同步真实状态
     */
    async removeFile(fileId) {
      const confirmed = confirm(
        '确定要删除这个文档吗？'
        + '删除后将同时移除该文档的向量索引。'
      );

      if (!confirmed) {
        return;
      }

      try {
        const deletingCurrent =
          this.uploadedFileId ===
          fileId;

        /**
         * 先删除后端真实数据。
         */
        await apiService
          .deleteDocument(
            fileId
          );

        /**
         * 如果删除的是当前文档，
         * 清掉当前选择。
         *
         * refreshDocuments()
         * 会自动选择剩余文档中的
         * 第一篇。
         */
        if (deletingCurrent) {
          this.uploadedFileId = '';

          localStorage.removeItem(
            'lastRagDocumentId'
          );
        }

        /**
         * 重新从 ChromaDB
         * 获取真实文档列表。
         */
        await this.refreshDocuments();

        if (
          this.uploadedFiles.length >
          0
        ) {
          this.currentStep = 'qa';
        } else {
          this.currentStep = 'init';
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


    /**
     * 从后端同步文档列表。
     *
     * ChromaDB 是文档状态
     * Source of Truth。
     */
    async refreshDocuments() {
      try {
        const result =
          await apiService
            .getDocuments();

        const documents =
          Array.isArray(
            result?.documents
          )
            ? result.documents
            : [];

        /**
         * 后端结构：
         *
         * document_id
         * file_name
         * file_type
         * uploaded_at
         * chunk_count
         *
         * 转换为前端展示结构。
         */
        this.uploadedFiles =
          documents.map(
            (document) => ({
              id:
                document
                  .document_id,

              name:
                document
                  .file_name,

              fileType:
                document
                  .file_type,

              chunkCount:
                document
                  .chunk_count,

              uploadedAt:
                document
                  .uploaded_at,

              /**
               * 保留 ISO 时间，
               * 统一交给 formatDate
               * 做展示格式化。
               */
              time:
                document
                  .uploaded_at ||
                ''
            })
          );

        /**
         * 旧版本使用的
         * LocalStorage 文档列表
         * 已经废弃。
         */
        localStorage.removeItem(
          'ragUploadedFiles'
        );

        /**
         * 如果当前选中的文档
         * 仍然真实存在，
         * 直接继续使用。
         */
        const currentExists =
          this.uploadedFiles.some(
            (file) =>
              file.id ===
              this.uploadedFileId
          );

        if (currentExists) {
          localStorage.setItem(
            'lastRagDocumentId',
            this.uploadedFileId
          );

          return;
        }

        /**
         * 尝试恢复用户上一次
         * 选择的文档。
         */
        const lastDocumentId =
          localStorage.getItem(
            'lastRagDocumentId'
          );

        const lastExists =
          this.uploadedFiles.find(
            (file) =>
              file.id ===
              lastDocumentId
          );

        if (lastExists) {
          this.uploadedFileId =
            lastExists.id;

          return;
        }

        /**
         * 如果之前的选择不存在，
         * 默认选择列表第一篇。
         */
        if (
          this.uploadedFiles.length >
          0
        ) {
          this.uploadedFileId =
            this.uploadedFiles[0].id;

          localStorage.setItem(
            'lastRagDocumentId',
            this.uploadedFileId
          );
        } else {
          /**
           * 后端知识库为空。
           */
          this.uploadedFileId = '';

          localStorage.removeItem(
            'lastRagDocumentId'
          );
        }

      } catch (error) {
        console.error(
          '同步文档列表失败:',
          error
        );

        this.showMessage(
          error.message ||
          '同步文档列表失败',
          'error'
        );
      }
    },


    /**
     * 格式化上传时间。
     */
    formatDate(dateString) {
      if (!dateString) {
        return '时间未知';
      }

      const date =
        new Date(dateString);

      if (
        Number.isNaN(
          date.getTime()
        )
      ) {
        return '时间未知';
      }

      return date.toLocaleString(
        'zh-CN',
        {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        }
      );
    },


    /**
     * 顶部提示消息。
     */
    showMessage(
      text,
      type = 'info'
    ) {
      this.message = text;

      this.messageType =
        type;

      setTimeout(
        () => {
          this.message = '';
        },
        3000
      );
    }
  }
};
</script>

<style
  scoped
  src="../styles/main.css"
>
</style>