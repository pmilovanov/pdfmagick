<template>
  <div class="page-navigator">
    <h3 class="section-title">📖 Page Navigation</h3>

    <div class="page-controls">
      <button
        @click="previousPage"
        :disabled="pdfStore.currentPage === 0"
        class="nav-btn"
      >
        ◀
      </button>

      <span class="page-info">
        Page {{ pdfStore.currentPage + 1 }} of {{ pdfStore.pdfInfo?.page_count || 0 }}
      </span>

      <button
        @click="nextPage"
        :disabled="!pdfStore.pdfInfo || pdfStore.currentPage >= pdfStore.pdfInfo.page_count - 1"
        class="nav-btn"
      >
        ▶
      </button>
    </div>

    <div class="page-slider">
      <input
        type="range"
        :min="0"
        :max="(pdfStore.pdfInfo?.page_count || 1) - 1"
        :value="pdfStore.currentPage"
        @input="setPage($event.target.value)"
        class="slider"
      />
    </div>

    <div class="batch-actions">
      <button @click="pdfStore.copyFiltersToAllPages()" class="action-btn">
        📋 Copy to All Pages
      </button>
      <button @click="pdfStore.autoEnhanceAllPages()" class="action-btn">
        ✨ Auto Enhance All Pages
      </button>
      <button @click="pdfStore.resetCurrentPage()" class="action-btn">
        🔄 Reset Current
      </button>
      <button @click="pdfStore.resetAllPages()" class="action-btn">
        🔄 Reset All
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePdfStore } from '~/stores/pdf'

const pdfStore = usePdfStore()

const previousPage = () => {
  if (pdfStore.currentPage > 0) {
    pdfStore.setCurrentPage(pdfStore.currentPage - 1)
  }
}

const nextPage = () => {
  if (pdfStore.pdfInfo && pdfStore.currentPage < pdfStore.pdfInfo.page_count - 1) {
    pdfStore.setCurrentPage(pdfStore.currentPage + 1)
  }
}

const setPage = (value: string | number) => {
  pdfStore.setCurrentPage(Number(value))
}
</script>

<style scoped>
.page-navigator {
  padding: 1.5rem;
  border-bottom: 1px solid #e5e5e7;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #1d1d1f;
}

.page-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.nav-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #d2d2d7;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-btn:hover:not(:disabled) {
  background: #f5f5f7;
}

.nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 0.875rem;
  color: #86868b;
}

.page-slider {
  margin-bottom: 1rem;
}

.slider {
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #d2d2d7;
  outline: none;
  -webkit-appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #007aff;
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #007aff;
  cursor: pointer;
}

.batch-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.action-btn {
  padding: 0.5rem;
  border: 1px solid #d2d2d7;
  background: white;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f5f5f7;
}
</style>