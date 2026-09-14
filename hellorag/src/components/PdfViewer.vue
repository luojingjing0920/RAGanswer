<template>
  <div class="pdf-viewer">
    <div
      v-if="pdfDocument && !error"
      class="pdf-toolbar"
    >
      <div class="pdf-toolbar-group">
        <button
          type="button"
          class="pdf-tool-btn"
          :disabled="viewerPage <= 1"
          @click="previousPage"
        >
          ‹
        </button>

        <span class="pdf-page-info">
          {{ viewerPage }}
          /
          {{ totalPages }}
        </span>

        <button
          type="button"
          class="pdf-tool-btn"
          :disabled="
            viewerPage >= totalPages
          "
          @click="nextPage"
        >
          ›
        </button>
      </div>

      <div class="pdf-toolbar-group">
        <button
          type="button"
          class="pdf-tool-btn"
          :disabled="zoom <= minZoom"
          @click="zoomOut"
        >
          −
        </button>

        <button
          type="button"
          class="pdf-zoom-value"
          title="恢复适应宽度"
          @click="resetZoom"
        >
          {{ zoomPercent }}%
        </button>

        <button
          type="button"
          class="pdf-tool-btn"
          :disabled="zoom >= maxZoom"
          @click="zoomIn"
        >
          +
        </button>
      </div>
    </div>

    <div
      ref="viewer"
      class="pdf-scroll-area"
    >
      <div
        v-if="isLoading"
        class="pdf-status"
      >
        正在加载 PDF...
      </div>

      <div
        v-else-if="error"
        class="pdf-status pdf-error"
      >
        {{ error }}
      </div>

      <div
        v-show="!isLoading &&!error" class="pdf-canvas-wrapper"
      >
        <div ref="pageStage" class="pdf-page-stage">
          <canvas ref="canvas" class="pdf-canvas"
        ></canvas>
          <div class="pdf-highlight-layer" aria-hidden="true">
            <div v-for="(rect, index) in highlightRects" :key="index" class="pdf-highlight-rect" :style="{ left: `${rect.left}px`, top: `${rect.top}px`, width: `${rect.width}px`, height: `${rect.height}px` }">
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import {markRaw} from 'vue';
import * as pdfjsLib from 'pdfjs-dist';

import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjsLib.GlobalWorkerOptions.workerSrc =
  workerUrl;

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
    },
    citationText: {
      type: String,
      default: ''
    }
  },

  data() {
    return {
      pdfDocument: null,
      loadingTask: null,
      renderTask: null,
      renderVersion: 0,

      isLoading: false,
      error: '',

      viewerPage: 1,
      totalPages: 0,

      highlightRects: [],

      zoom: 1,
      minZoom: 0.75,
      maxZoom: 2,
      zoomStep: 0.25
    };
  },

  computed: {
    fileUrl() {
      if (!this.documentId) {
        return '';
      }

      const baseUrl =
        import.meta.env
          .VITE_API_BASE_URL || '';

      return `${
        baseUrl
      }/api/rag/documents/${
        encodeURIComponent(
          this.documentId
        )
      }/file`;
    },
     zoomPercent() {
        return Math.round(
          this.zoom * 100
        );
      }
  },

  watch: {
    documentId() {
      this.loadDocument();
    },

    page(newPage,oldPage) {
      if(newPage === oldPage) {
        return;
      }
      this.syncCitationPage(newPage);
    },

    citationText(
      newText,
      oldText
    ) {
      if (
        newText === oldText ||
        !this.pdfDocument
      ) {
        return;
      }

      this.renderPage(
        this.viewerPage
      );
    }
  },

  mounted() {
    this.loadDocument();
  },

  beforeUnmount() {
    this.cleanup();
  },

  methods: {
    async loadDocument() {
      if (!this.fileUrl) {
        return;
      }

      this.isLoading = true;
      this.error = '';

      try {
        await this.destroyDocument();

        this.loadingTask =
          markRaw(
            pdfjsLib.getDocument({
              url: this.fileUrl
            })
          );

        this.pdfDocument =
          markRaw(
            await this.loadingTask.promise
          );
        
        this.totalPages =
          this.pdfDocument.numPages;

        this.zoom = 1;

        await this.syncCitationPage(
          this.page
        );

      } catch (error) {
        console.error(
          'PDF 加载失败:',
          error
        );

        this.error =
          'PDF 加载失败，请稍后重试';

      } finally {
        this.isLoading = false;
      }
    },

    normalizeText(text) {
      return String(
        text || ''
      )
        .replace(/\s+/g, '');
    },

    buildHighlightRects(
      items,
      viewport,
      citationText
    ) {
      const normalizedCitation =
        this.normalizeText(
          citationText
        );

      if (
        !normalizedCitation ||
        !items?.length
      ) {
        return [];
      }
    
      let combinedText = '';
    
      const mappedItems = [];
    
      for (const item of items) {
        const normalizedItem =
          this.normalizeText(
            item.str
          );
      
        if (!normalizedItem) {
          continue;
        }
      
        const start =
          combinedText.length;
      
        combinedText +=
          normalizedItem;
      
        mappedItems.push({
          item,
          start,
          end:
            combinedText.length
        });
      }
    
      let matchStart =
        combinedText.indexOf(
          normalizedCitation
        );
    
      let matchLength =
        normalizedCitation.length;
    
      /*
       * Chunk 与 PDF TextContent
       * 可能存在少量排版差异。
       *
       * 完整文本无法匹配时，
       * 使用前部特征文本降级匹配。
       */
      if (matchStart < 0) {
        const fallbackLengths = [
          120,
          80,
          50,
          30
        ];
      
        for (
          const length
          of fallbackLengths
        ) {
          if (
            normalizedCitation.length <
            length
          ) {
            continue;
          }
        
          const anchor =
            normalizedCitation.slice(
              0,
              length
            );
        
          const anchorStart =
            combinedText.indexOf(
              anchor
            );
        
          if (anchorStart >= 0) {
            matchStart =
              anchorStart;
          
            matchLength =
              length;
          
            break;
          }
        }
      }
    
      if (matchStart < 0) {
        return [];
      }
    
      const matchEnd =
        matchStart +
        matchLength;
    
      const matchedItems =
        mappedItems.filter(
          ({ start, end }) => (
            end > matchStart &&
            start < matchEnd
          )
        );
    
      return matchedItems
        .map(({ item }) => (
          this.createHighlightRect(
            item,
            viewport
          )
        ))
        .filter(Boolean);
    },

    createHighlightRect(
      item,
      viewport
    ) {
      if (
        !item?.transform ||
        !item.str
      ) {
        return null;
      }
    
      const transform =
        pdfjsLib.Util.transform(
          viewport.transform,
          item.transform
        );
    
      const fontHeight =
        Math.hypot(
          transform[2],
          transform[3]
        );
    
      const width =
        Math.max(
          item.width *
            viewport.scale,
          2
        );
    
      return {
        left:
          transform[4],
      
        top:
          transform[5] -
          fontHeight,
      
        width,
      
        height:
          Math.max(
            fontHeight * 1.15,
            4
          )
      };
    },

    async renderPage(targetPage = this.viewerPage) {
      if (!this.pdfDocument) {
        return;
      }

      const currentRenderVersion =
        ++this.renderVersion;

      this.highlightRects = [];

      try {
        if (this.renderTask) {
          this.renderTask.cancel();
          this.renderTask = null;
        }

        const pageNumber =
          this.normalizePage(
            targetPage
          );  
        this.viewerPage =
          pageNumber;

        const pdfPage =
          await this.pdfDocument
            .getPage(pageNumber);

        if (
          currentRenderVersion !==
          this.renderVersion
        ) {
          return;
        }

        const canvas =
          this.$refs.canvas;

        const viewer =
          this.$refs.viewer;

        const pageStage =
          this.$refs.pageStage;

        if (
          !canvas ||
          !viewer ||
          !pageStage
        ) {
          return;
        }

        const baseViewport =
          pdfPage.getViewport({
            scale: 1
          });

        const availableWidth =
          Math.max(
            viewer.clientWidth - 32,
            320
          );
        
        const fitScale =
          availableWidth /
          baseViewport.width;

        const scale =
          fitScale * this.zoom;

        const viewport =
          pdfPage.getViewport({
            scale
          });

        const outputScale =
          window.devicePixelRatio || 1;

        canvas.width =
          Math.floor(
            viewport.width *
            outputScale
          );

        canvas.height =
          Math.floor(
            viewport.height *
            outputScale
          );

        canvas.style.width =
          `${viewport.width}px`;

        canvas.style.height =
          `${viewport.height}px`;

        pageStage.style.width =
          `${viewport.width}px`;

        pageStage.style.height =
          `${viewport.height}px`;

        const context =
          canvas.getContext('2d');

        const transform =
          outputScale !== 1
            ? [
                outputScale,
                0,
                0,
                outputScale,
                0,
                0
              ]
            : null;

        this.renderTask =
          markRaw(
            pdfPage.render({
              canvasContext:
                context,
              viewport,
              transform
            })
          );

        await this.renderTask.promise;

        this.renderTask = null;

        if(currentRenderVersion !== this.renderVersion) {
          return;
        }

        const textContent =
          await pdfPage.getTextContent();

        if(currentRenderVersion !== this.renderVersion) {
          return;
        }

        this.highlightRects =
          this.buildHighlightRects(
            textContent.items,
            viewport,
            this.citationText
          );

      } catch (error) {
        if (
          error?.name ===
          'RenderingCancelledException'
        ) {
          return;
        }

        console.error(
          'PDF 页面渲染失败:',
          error
        );

        this.error =
          'PDF 页面渲染失败';
      }
    },

    normalizePage(page) {
      const parsedPage =
        Number(page);

      if (
        !Number.isFinite(
          parsedPage
        )
      ) {
        return 1;
     }

      const totalPages =
        this.totalPages || 1;

      return Math.min(
        Math.max(
          Math.round(parsedPage),
          1
        ),
        totalPages
      );
    },

    async previousPage() {
      if (
        this.viewerPage <= 1
      ) {
        return;
      }

      this.viewerPage -= 1;

      await this.renderPage(this.viewerPage);

      this.scrollToTop();
    },

    async nextPage() {
      if (
        this.viewerPage >=
        this.totalPages
      ) {
        return;
      }

      this.viewerPage += 1;

      await this.renderPage(this.viewerPage);

      this.scrollToTop();
    },

    async zoomIn() {
      if (
        this.zoom >=
        this.maxZoom
      ) {
        return;
      }

      this.zoom =
        Math.min(
          this.zoom +
            this.zoomStep,
          this.maxZoom
        );

      await this.renderPage(this.viewerPage);
    },

    async zoomOut() {
      if (
        this.zoom <=
        this.minZoom
      ) {
        return;
      }

      this.zoom =
        Math.max(
          this.zoom -
            this.zoomStep,
          this.minZoom
        );

      await this.renderPage(this.viewerPage);
    },

    async resetZoom() {
      this.zoom = 1;

      await this.renderPage(this.viewerPage);
    },

    scrollToTop() {
      const viewer =
        this.$refs.viewer;

      if (!viewer) {
        return;
      }

      viewer.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    },

    async destroyDocument() {
      if (this.renderTask) {
        this.renderTask.cancel();
        this.renderTask = null;
      }

      if (this.loadingTask) {
        try {
          await this.loadingTask.destroy();
        } catch (error) {
          console.warn(
            'PDF LoadingTask 清理失败:',
            error
          );
        }

        this.loadingTask = null;
      }

      this.pdfDocument = null;
    },

    async syncCitationPage(page) {
      const targetPage =
        this.normalizePage(page);

      this.viewerPage =
        targetPage;

      if (!this.pdfDocument) {
        return;
      }

      await this.renderPage(
        targetPage
      );

      this.scrollToTop();
    },

    cleanup() {
      this.destroyDocument();
    }
  }
};
</script>

<style
  scoped
  src="../styles/pdf-viewer.css"
>
</style>