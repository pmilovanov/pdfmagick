<template>
  <div class="pdf-details">
    <h3 class="section-title">📋 PDF Details</h3>

    <div v-if="pdfStore.pdfInfo" class="details-content">
      <div class="detail-item">
        <span class="detail-label">Filename:</span>
        <span class="detail-value">{{ pdfStore.pdfInfo.filename }}</span>
      </div>

      <div class="detail-item">
        <span class="detail-label">Page count:</span>
        <span class="detail-value">{{ pdfStore.pdfInfo.page_count }} pages</span>
      </div>

      <div v-if="currentPageDimensions" class="detail-item">
        <span class="detail-label">Current page ({{ pdfStore.currentPage + 1 }}):</span>
        <span class="detail-value">
          {{ currentPageDimensions.width_inches.toFixed(1) }} × {{ currentPageDimensions.height_inches.toFixed(1) }} inches
        </span>
      </div>

      <div v-if="currentPageDimensions" class="detail-item">
        <span class="detail-label">Preview resolution:</span>
        <span class="detail-value">
          {{ effectiveDpi }} DPI
          <span v-if="isScaledDown" class="scaled-indicator">(scaled from 150 DPI)</span>
        </span>
      </div>

      <div v-if="currentPageDimensions" class="detail-item">
        <span class="detail-label">Preview size:</span>
        <span class="detail-value">
          {{ previewWidth }} × {{ previewHeight }} px
          ({{ megapixels.toFixed(1) }} MP)
        </span>
      </div>

      <details v-if="showAdvanced" class="advanced-details">
        <summary class="detail-label">All page dimensions</summary>
        <div class="pages-list">
          <div v-for="(dim, idx) in pdfStore.pdfInfo.page_dimensions" :key="idx" class="page-dim-item">
            <span>Page {{ idx + 1 }}:</span>
            <span>{{ dim.width_inches.toFixed(1) }} × {{ dim.height_inches.toFixed(1) }} inches</span>
          </div>
        </div>
      </details>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { usePdfStore } from '~/stores/pdf'

const pdfStore = usePdfStore()

const props = defineProps<{
  showAdvanced?: boolean
}>()

const currentPageDimensions = computed(() => {
  if (!pdfStore.pdfInfo || pdfStore.currentPage >= pdfStore.pdfInfo.page_dimensions.length) {
    return null
  }
  return pdfStore.pdfInfo.page_dimensions[pdfStore.currentPage]
})

const effectiveDpi = computed(() => {
  if (!currentPageDimensions.value) return 150

  const { width_inches, height_inches } = currentPageDimensions.value
  const maxDimension = Math.max(width_inches, height_inches)

  // Scale down DPI for very large pages to keep preview manageable
  // Target max dimension of ~2000px for preview
  if (maxDimension > 13.3) {  // Would be >2000px at 150 DPI
    return Math.floor(2000 / maxDimension)
  }

  return 150
})

const isScaledDown = computed(() => effectiveDpi.value < 150)

const previewWidth = computed(() => {
  if (!currentPageDimensions.value) return 0
  return Math.floor(currentPageDimensions.value.width_inches * effectiveDpi.value)
})

const previewHeight = computed(() => {
  if (!currentPageDimensions.value) return 0
  return Math.floor(currentPageDimensions.value.height_inches * effectiveDpi.value)
})

const megapixels = computed(() => {
  return (previewWidth.value * previewHeight.value) / 1_000_000
})
</script>

<style scoped>
.pdf-details {
  padding: 1.5rem;
  border-bottom: 1px solid #e5e5e7;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #1d1d1f;
}

.details-content {
  font-size: 0.875rem;
}

.detail-item {
  margin-bottom: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  color: #86868b;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  color: #1d1d1f;
  font-weight: 500;
}

.scaled-indicator {
  color: #007aff;
  font-size: 0.75rem;
  font-weight: normal;
}

.advanced-details {
  margin-top: 1rem;
}

.advanced-details summary {
  cursor: pointer;
  user-select: none;
  margin-bottom: 0.5rem;
}

.advanced-details summary:hover {
  color: #007aff;
}

.pages-list {
  margin-top: 0.5rem;
  padding-left: 1rem;
  max-height: 200px;
  overflow-y: auto;
}

.page-dim-item {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
  font-size: 0.75rem;
  color: #86868b;
}
</style>