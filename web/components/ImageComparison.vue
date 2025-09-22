<template>
  <div class="image-comparison">
    <div class="comparison-container">
      <!-- Original Image -->
      <div class="image-pane">
        <h3 class="pane-title">📄 Original - Page {{ pdfStore.currentPage + 1 }}</h3>
        <div class="image-wrapper">
          <img
            v-if="originalImage"
            :src="originalImage"
            alt="Original"
            class="preview-image"
          />
          <div v-else class="image-placeholder">
            <span v-if="pdfStore.isLoading">Loading...</span>
            <span v-else>No image</span>
          </div>
        </div>
      </div>

      <!-- Processed Image -->
      <div class="image-pane">
        <h3 class="pane-title">✨ Processed - Page {{ pdfStore.currentPage + 1 }}</h3>
        <div class="image-wrapper">
          <img
            v-if="processedImage"
            :src="processedImage"
            alt="Processed"
            class="preview-image"
          />
          <div v-else class="image-placeholder">
            <span v-if="pdfStore.isLoading">Processing...</span>
            <span v-else>No image</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Status Bar -->
    <div v-if="hasFilters" class="status-bar">
      ✅ Filters applied to this page
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePdfStore } from '~/stores/pdf'

const pdfStore = usePdfStore()

const originalImage = computed(() => {
  return pdfStore.originalImages.get(pdfStore.currentPage)
})

const processedImage = computed(() => {
  return pdfStore.processedImages.get(pdfStore.currentPage)
})

const hasFilters = computed(() => {
  const filters = pdfStore.pageFilters.get(pdfStore.currentPage)
  if (!filters) return false

  const defaults = pdfStore.getDefaultFilters()
  return JSON.stringify(filters) !== JSON.stringify(defaults)
})
</script>

<style scoped>
.image-comparison {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.comparison-container {
  flex: 1;
  display: flex;
  gap: 2rem;
  min-height: 0;
}

.image-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.pane-title {
  padding: 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: #1d1d1f;
  border-bottom: 1px solid #e5e5e7;
}

.image-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  overflow: auto;
  background: #fafafa;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.image-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #86868b;
  font-size: 0.875rem;
}

.status-bar {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #34c759;
  color: white;
  border-radius: 6px;
  text-align: center;
  font-size: 0.875rem;
  font-weight: 500;
}
</style>