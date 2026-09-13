<template>
  <details class="source-card">
    <summary>
      <span class="source-index">
        [{{ source.source_id }}]
      </span>

      <span class="source-file">
        {{ source.file_name }}
      </span>

      <span class="source-location">
        {{ sourceLocation }}
      </span>

      <button
        v-if="canPreview"
        type="button"
        class="source-preview-btn"
        @click.stop="handlePreview"
      >
        查看原文
      </button>
    </summary>

    <div class="source-meta">
      语义相关度：
      {{ similarityText }}
    </div>

    <div class="source-text">
      {{ source.text }}
    </div>
  </details>
</template>

<script>
export default {
  name: 'SourceCard',

  props: {
    source: {
      type: Object,
      required: true
    }
  },

  emits: [
    'preview'
  ],

  computed: {
    sourceLocation() {
      if (
        this.source.page !== null &&
        this.source.page !== undefined
      ) {
        return `第 ${this.source.page} 页`;
      }

      if (
        this.source.chunk_index !== null &&
        this.source.chunk_index !== undefined
      ) {
        return `片段 ${
          this.source.chunk_index + 1
        }`;
      }

      return '文档片段';
    },

    similarityText() {
      const similarity =
        this.source.similarity;

      if (
        typeof similarity !== 'number'
      ) {
        return '-';
      }

      return `${
        (
          similarity * 100
        ).toFixed(1)
      }%`;
    },

    canPreview() {
        const fileName =
            this.source.file_name || '';

        return Boolean(
            this.source.document_id &&
            this.source.page !== null &&
            this.source.page !== undefined &&
            fileName
            .toLowerCase()
            .endsWith('.pdf')
        );
    }
  },

  methods: {
    handlePreview() {
      this.$emit(
        'preview',
        this.source
      );
    }
  }
};
</script>

<style
  scoped
  src="../styles/source-card.css"
>
</style>