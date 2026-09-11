<template>
  <div class="file-upload-container">
    <h3>文档上传</h3>
    
    <div class="upload-methods">
      <!-- 文件上传 -->
      <div class="upload-method">
        <h4>本地上传</h4>
        <div class="upload-area" 
             :class="{ 'dragging': isDragging }"
             @dragover.prevent="handleDragOver"
             @dragleave.prevent="handleDragLeave"
             @drop.prevent="handleDrop">
          <input type="file" 
                 ref="fileInput" 
                 @change="handleFileSelect"
                 accept=".docx,.pdf,.md,.txt">
          <div class="upload-prompt">
            <span v-if="selectedFile">已选择: {{ selectedFile.name }}</span>
            <span v-else>点击或拖拽文件到此处上传</span>
          </div>
        </div>
        <p class="file-tips">支持docx、pdf、md、txt 格式，最大 20MB</p>
      </div>
    </div>


    <div class="upload-actions">
      <button @click="handleUpload" 
              :disabled="!canUpload || isUploading" 
              class="upload-btn">
        {{ isUploading ? '上传中...' : '上传文档' }}
      </button>
    </div>

    <div
      v-if="uploadResult"
      class="upload-result"
    >
      <h4>文档索引完成</h4>

      <div class="file-info">
        <p>
          文件名：
          {{ uploadResult.file_name }}
        </p>

        <p>
          文档类型：
          {{ uploadResult.file_type }}
        </p>

        <p>
          文档切片：
          {{ uploadResult.chunk_count }}
        </p>

        <p>
          向量维度：
          {{
            uploadResult.embedding_dimension
          }}
        </p>
      </div>
    </div>

    <div v-if="error" class="error-message">
      <p>{{ error }}</p>
    </div>
  </div>
</template>

<script>
import apiService
  from '../services/apiService';

export default {
  name: 'FileUpload',

  data() {
    return {
      selectedFile: null,

      isDragging: false,

      isUploading: false,

      uploadResult: null,

      error: null
    };
  },

  computed: {
    canUpload() {
      return (
        this.selectedFile &&
        !this.isUploading
      );
    }
  },

  methods: {
    handleFileSelect(event) {
      const file =
        event.target.files[0];

      if (file) {
        this.validateFile(file);
      }
    },

    handleDragOver() {
      this.isDragging = true;
    },

    handleDragLeave() {
      this.isDragging = false;
    },

    handleDrop(event) {
      this.isDragging = false;

      const file =
        event.dataTransfer.files[0];

      if (file) {
        this.validateFile(file);
      }
    },

    validateFile(file) {
      if (
        file.size >
        20 * 1024 * 1024
      ) {
        this.error =
          '文件大小不能超过20MB';

        return;
      }

      const validTypes = [
        '.docx',
        '.pdf',
        '.md',
        '.txt'
      ];

      const fileExt =
        file.name
          .toLowerCase()
          .substring(
            file.name.lastIndexOf('.')
          );

      if (
        !validTypes.includes(
          fileExt
        )
      ) {
        this.error =
          '不支持的文件类型，请上传 PDF、DOCX、MD、TXT 文件';

        return;
      }

      this.selectedFile = file;
      this.uploadResult = null;
      this.error = null;
    },

    async handleUpload() {
      if (
        !this.selectedFile ||
        this.isUploading
      ) {
        return;
      }

      await this.uploadLocalFile();
    },

    async uploadLocalFile() {
      if (!this.selectedFile) {
        this.error = '请选择文件';

        return;
      }

      this.isUploading = true;
      this.error = null;

      /**
       * 防止后面 selectedFile
       * 被清空以后拿不到文件名。
       */
      const currentFile =
        this.selectedFile;

      try {
        const result =
          await apiService
            .uploadDocument(
              currentFile
            );

        if (
          result.status ===
            'success' &&
          result.document_id
        ) {
          this.uploadResult =
            result;

          /**
           * 新版本传给父组件的已经不是
           * 讯飞 fileId，
           * 而是我们自己的 document_id。
           */
          this.$emit(
            'file-uploaded',
            result.document_id,
            result.file_name ||
              currentFile.name
          );

          this.selectedFile = null;

          if (
            this.$refs.fileInput
          ) {
            this.$refs
              .fileInput
              .value = '';
          }

        } else {
          this.error =
            '文档索引失败';
        }

      } catch (error) {
        console.error(
          '本地文档索引失败:',
          error
        );

        this.error =
          error.message ||
          '上传失败，请稍后重试';

      } finally {
        this.isUploading = false;
      }
    }
  }
};
</script>

<style scoped>
.file-upload-container {
  width: 100%;
  padding: 25px;
  background: #f9f9f9;
  border-radius: 12px;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
}

h3 {
  margin-top: 0;
  margin-bottom: 25px;
  color: #333;
  text-align: center;
  font-size: 24px;
}

.upload-methods {
  display: flex;
  gap: 30px;
  margin-bottom: 25px;
  flex-wrap: wrap;
}

.upload-method {
  flex: 1;
  min-width: 300px;
}

.upload-method h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #666;
  font-size: 18px;
  font-weight: 500;
}

.upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 40px 30px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
}

.upload-area:hover {
  border-color: #409eff;
  background: #f0f7ff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.upload-area.dragging {
  border-color: #409eff;
  background: #e6f0ff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
}

.upload-area input[type="file"] {
  position: absolute;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.upload-prompt {
  font-size: 16px;
  color: #666;
  font-weight: 500;
}

.file-tips {
  margin-top: 10px;
  font-size: 13px;
  color: #999;
  text-align: center;
}

.url-upload {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.url-input,
.name-input {
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  transition: all 0.3s ease;
  background: white;
}

.url-input:focus,
.name-input:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
}

.upload-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  flex-wrap: wrap;
  gap: 25px;
  padding: 15px;
  background: white;
  border-radius: 8px;
}

.upload-options label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 16px;
  color: #666;
}

.upload-actions {
  display: flex;
  justify-content: center;
  margin-bottom: 25px;
}

.upload-btn {
  padding: 12px 40px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 18px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.upload-btn:hover:not(:disabled) {
  background: #66b1ff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.upload-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.upload-result {
  background: #f0f9ff;
  border: 1px solid #b3e5fc;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 15px;
}

.upload-result h4 {
  margin-top: 0;
  color: #0288d1;
}

.upload-result pre {
  background: white;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
  color: #333;
}

.file-info p {
  margin: 5px 0;
  font-size: 14px;
  color: #666;
}

.error-message {
  background: #ffebee;
  border: 1px solid #ffcdd2;
  border-radius: 4px;
  padding: 15px;
  color: #c62828;
}

@media (max-width: 768px) {
  .upload-methods {
    flex-direction: column;
  }
}
</style>