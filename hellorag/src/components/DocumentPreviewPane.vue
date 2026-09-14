<template>
  <section class="preview-pane">
    <header class="preview-header">
      <div class="preview-title">
        <span class="preview-icon">
          📄
        </span>

        <div class="preview-file-info">
          <div class="preview-label">
            原文预览
          </div>

          <div
            class="preview-file-name"
            :title="fileName"
          >
            {{ fileName }}
          </div>
        </div>
      </div>

      <div class="preview-actions">
        <span
          v-if="page !== null"
          class="preview-page"
        >
          引用第 {{ page }} 页
        </span>

        <button
          type="button"
          class="preview-close-btn"
          title="关闭预览"
          @click="handleClose"
        >
          ×
        </button>
      </div>
    </header>

    <div class="preview-content">
      <PdfViewer
        :document-id="documentId"
        :page="page"
        :citation-text="citationText"
      />
    </div>
  </section>
</template>

<script>
import PdfViewer
  from './PdfViewer.vue';

export default {
  name: 'DocumentPreviewPane',

  components: {
    PdfViewer
  },

  props: {
    documentId: {
      type: String,
      required: true
    },

    fileName: {
      type: String,
      default: 'PDF 文档'
    },

    page: {
      type: Number,
      default: null
    },
    citationText: {
      type: String,
      default: ''
    }
  },

  emits: [
    'close'
  ],

  methods: {
    handleClose() {
      this.$emit('close');
    }
  }
};
</script>

<style
  scoped
  src="../styles/document-preview-pane.css"
>
</style>