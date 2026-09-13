<template>
  <div
    v-if="sources.length"
    class="source-list"
  >
    <div class="source-title-row">
      <div class="source-title">
        参考来源
      </div>

      <div class="source-scope-info">
        {{ sourceScopeText }}
      </div>
    </div>

    <SourceCard
      v-for="source in sources"
      :key="getSourceKey(source)"
      :source="source"
      @preview="handlePreview"
    />
  </div>
</template>

<script>
import SourceCard
  from './SourceCard.vue';

export default {
  name: 'SourceList',

  components: {
    SourceCard
  },

  props: {
    sources: {
      type: Array,
      default: () => []
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
    'preview'
  ],

  computed: {
    /**
     * 当前 Sources 实际命中的
     * 文档数量。
     */
    hitDocumentCount() {
      const documentKeys =
        this.sources
          .map((source) => (
            source.document_id ||
            source.file_name
          ))
          .filter(Boolean);

      return new Set(
        documentKeys
      ).size;
    },

    /**
     * Source 列表右上角
     * 检索范围说明。
     */
    sourceScopeText() {
      if (
        this.retrievalScope === 'all'
      ) {
        return (
          `全部文档 · 命中 ${
            this.hitDocumentCount
          } 个文档`
        );
      }

      return '当前文档';
    }
  },

  methods: {
    /**
     * 为每一条 Source
     * 生成稳定的 Vue key。
     */
    getSourceKey(source) {
      const documentKey =
        source.document_id ||
        source.file_name ||
        'source';

      return `${
        documentKey
      }-${
        source.source_id
      }-${
        source.chunk_index
      }`;
    },

    /**
     * SourceCard 不负责决定
     * PDF Preview 放在哪里。
     *
     * 它只把点击事件继续
     * 向父组件传递。
     */
    handlePreview(source) {
      this.$emit(
        'preview',
        source
      );
    }
  }
};
</script>

<style
  scoped
  src="../styles/source-list.css"
>
</style>