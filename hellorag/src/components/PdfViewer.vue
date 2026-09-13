<template>
  <div class="pdf-viewer">
    <iframe
      v-if="pdfUrl"
      :key="viewerKey"
      :src="pdfUrl"
      class="pdf-frame"
      title="PDF 文档预览"
    ></iframe>

    <div
      v-else
      class="pdf-empty"
    >
      暂无可预览文档
    </div>
  </div>
</template>

<script>
export default {
  name: 'PdfViewer',

  props: {
    documentId: {
      type: String,
      default: ''
    },

    page: {
      type: Number,
      default: null
    }
  },

  computed: {
    viewerKey() {
      return `${
        this.documentId
      }-${
        this.page ?? 'default'
      }`;
    },

    pdfUrl() {
      if (!this.documentId) {
        return '';
      }

      const baseUrl =
        import.meta.env
          .VITE_API_BASE_URL || '';

      const fileUrl =
        `${baseUrl}/api/rag/documents/${
          encodeURIComponent(
            this.documentId
          )
        }/file`;

      if (
        this.page !== null &&
        this.page !== undefined
      ) {
        return `${fileUrl}#page=${
          this.page
        }`;
      }

      return fileUrl;
    }
  }
};
</script>

<style
  scoped
  src="../styles/pdf-viewer.css"
>
</style>