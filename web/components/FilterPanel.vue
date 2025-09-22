<template>
  <div class="filter-panel">
    <h3 class="section-title">🎛️ Image Adjustments</h3>

    <button @click="autoEnhance" class="auto-enhance-btn">
      ✨ Auto Enhance
    </button>

    <!-- Basic Adjustments -->
    <details open class="filter-group">
      <summary class="group-title">🔆 Basic Adjustments</summary>
      <div class="filter-controls">
        <FilterSlider
          label="Brightness"
          v-model="filters.brightness"
          :min="-100"
          :max="100"
          @update:modelValue="updateFilters"
        />
        <FilterSlider
          label="Contrast"
          v-model="filters.contrast"
          :min="-100"
          :max="100"
          @update:modelValue="updateFilters"
        />
        <FilterSlider
          label="Exposure"
          v-model="filters.exposure"
          :min="-3"
          :max="3"
          :step="0.1"
          @update:modelValue="updateFilters"
        />
      </div>
    </details>

    <!-- Tonal Adjustments -->
    <details class="filter-group">
      <summary class="group-title">💡 Tonal Adjustments</summary>
      <div class="filter-controls">
        <FilterSlider
          label="Highlights"
          v-model="filters.highlights"
          :min="-100"
          :max="100"
          @update:modelValue="updateFilters"
        />
        <FilterSlider
          label="Midtones"
          v-model="filters.midtones"
          :min="-100"
          :max="100"
          @update:modelValue="updateFilters"
        />
        <FilterSlider
          label="Shadows"
          v-model="filters.shadows"
          :min="-100"
          :max="100"
          @update:modelValue="updateFilters"
        />
      </div>
    </details>

    <!-- Color Adjustments -->
    <details class="filter-group">
      <summary class="group-title">🎨 Color Adjustments</summary>
      <div class="filter-controls">
        <FilterSlider
          label="Saturation"
          v-model="filters.saturation"
          :min="-100"
          :max="100"
          @update:modelValue="updateFilters"
        />
        <FilterSlider
          label="Vibrance"
          v-model="filters.vibrance"
          :min="-100"
          :max="100"
          @update:modelValue="updateFilters"
        />
      </div>
    </details>

    <!-- Levels & Curves -->
    <details class="filter-group">
      <summary class="group-title">📊 Levels & Curves</summary>
      <div class="filter-controls">
        <FilterSlider
          label="Black Point"
          v-model="filters.black_point"
          :min="0"
          :max="255"
          @update:modelValue="updateFilters"
        />
        <FilterSlider
          label="White Point"
          v-model="filters.white_point"
          :min="0"
          :max="255"
          @update:modelValue="updateFilters"
        />
        <FilterSlider
          label="Gamma"
          v-model="filters.gamma"
          :min="0.1"
          :max="3"
          :step="0.01"
          @update:modelValue="updateFilters"
        />
      </div>
    </details>

    <!-- Sharpness -->
    <details class="filter-group">
      <summary class="group-title">🔍 Sharpness</summary>
      <div class="filter-controls">
        <FilterSlider
          label="Sharpness"
          v-model="filters.sharpness"
          :min="-100"
          :max="100"
          @update:modelValue="updateFilters"
        />
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { usePdfStore } from '~/stores/pdf'
import { debounce } from 'lodash-es'

const pdfStore = usePdfStore()

const filters = ref({ ...pdfStore.currentPageFilters })

// Watch for page changes AND filter changes
watch([() => pdfStore.currentPage, () => pdfStore.currentPageFilters], () => {
  filters.value = { ...pdfStore.currentPageFilters }
}, { deep: true })

// Debounced filter update
const updateFilters = debounce(() => {
  pdfStore.applyFilters(pdfStore.currentPage, { ...filters.value })
}, 50)

const autoEnhance = () => {
  // Simple auto-enhance logic
  filters.value = {
    ...pdfStore.getDefaultFilters(),
    contrast: 5,
    brightness: 2,
    black_point: 10,
    white_point: 245
  }
  updateFilters()
}
</script>

<style scoped>
.filter-panel {
  padding: 1.5rem;
  overflow-y: auto;
  max-height: calc(100vh - 300px);
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #1d1d1f;
}

.auto-enhance-btn {
  width: 100%;
  padding: 0.5rem;
  margin-bottom: 1rem;
  border: 1px solid #007aff;
  background: white;
  color: #007aff;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.auto-enhance-btn:hover {
  background: #007aff;
  color: white;
}

.filter-group {
  margin-bottom: 1rem;
  border: 1px solid #e5e5e7;
  border-radius: 6px;
  overflow: hidden;
}

.group-title {
  padding: 0.75rem 1rem;
  background: #f5f5f7;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  user-select: none;
}

.group-title:hover {
  background: #ebebed;
}

.filter-controls {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

details[open] .group-title {
  border-bottom: 1px solid #e5e5e7;
}
</style>