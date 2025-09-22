<template>
  <div v-if="visible" class="export-dialog-overlay" @click.self="close">
    <div class="export-dialog">
      <h2>💾 Export PDF Settings</h2>

      <!-- Page Size Override -->
      <div class="export-section">
        <h3>📐 Page Size</h3>
        <select v-model="exportSettings.pageSize" class="select-input">
          <option value="">Auto (use PDF dimensions)</option>
          <option value="letter">Letter (8.5 × 11 in)</option>
          <option value="letter-landscape">Letter Landscape (11 × 8.5 in)</option>
          <option value="a4">A4 (8.27 × 11.69 in)</option>
          <option value="a4-landscape">A4 Landscape (11.69 × 8.27 in)</option>
          <option value="legal">Legal (8.5 × 14 in)</option>
          <option value="tabloid">Tabloid (11 × 17 in)</option>
          <option value="a3">A3 (11.69 × 16.54 in)</option>
        </select>

        <label v-if="exportSettings.pageSize" class="checkbox-label">
          <input type="checkbox" v-model="exportSettings.padToExactSize" />
          📏 Pad to exact page size (for trimming)
        </label>

        <div v-if="exportSettings.padToExactSize" class="input-group">
          <label>First page to align left (odd):</label>
          <input
            type="number"
            v-model.number="exportSettings.firstOddPage"
            min="1"
            :max="pdfStore.pdfInfo?.page_count || 1"
            class="number-input"
          />
        </div>
      </div>

      <!-- 2-up Layout -->
      <div v-if="exportSettings.pageSize" class="export-section">
        <h3>📖 Layout</h3>
        <label class="checkbox-label">
          <input type="checkbox" v-model="exportSettings.twoUpEnabled" />
          2-up layout (2 pages per sheet)
        </label>

        <div v-if="exportSettings.twoUpEnabled">
          <div class="input-group">
            <label>Vertical alignment:</label>
            <select v-model="exportSettings.verticalAlign" class="select-input">
              <option value="top">Top</option>
              <option value="center">Center</option>
            </select>
          </div>

          <div class="input-group">
            <label>Layout mode:</label>
            <select v-model="exportSettings.layoutMode" class="select-input">
              <option value="sequential">Sequential</option>
              <option value="cut_and_stack">Cut & Stack</option>
            </select>
          </div>

          <div v-if="exportSettings.layoutMode === 'cut_and_stack'" class="input-group">
            <label>Start from page:</label>
            <input
              type="number"
              v-model.number="exportSettings.startPage"
              min="1"
              :max="pdfStore.pdfInfo?.page_count || 1"
              class="number-input"
            />
            <div class="info-text">
              🔪 Cut & Stack: Print double-sided, cut vertically, stack halves
            </div>
          </div>
        </div>
      </div>

      <!-- Page Numbering -->
      <div class="export-section">
        <h3>🔢 Page Numbers</h3>
        <label class="checkbox-label">
          <input type="checkbox" v-model="exportSettings.addPageNumbers" />
          Add page numbers
        </label>

        <div v-if="exportSettings.addPageNumbers" class="page-number-options">
          <div class="input-group">
            <label>Format:</label>
            <select v-model="exportSettings.pageNumberFormat" class="select-input">
              <option value="Page {n}">Page {n}</option>
              <option value="{n}">{n}</option>
              <option value="{n} of {total}">{n} of {total}</option>
            </select>
          </div>

          <div class="input-group">
            <label>Font size:</label>
            <input
              type="number"
              v-model.number="exportSettings.pageNumberSize"
              min="8"
              max="24"
              class="number-input"
            />
          </div>
        </div>
      </div>

      <!-- Export Quality -->
      <div class="export-section">
        <h3>🎯 Export Quality</h3>
        <div class="input-group">
          <label>DPI:</label>
          <select v-model.number="exportSettings.dpi" class="select-input">
            <option :value="150">150 DPI (Draft)</option>
            <option :value="200">200 DPI (Good)</option>
            <option :value="300">300 DPI (High)</option>
            <option :value="400">400 DPI (Very High)</option>
          </select>
        </div>

        <div class="input-group">
          <label>Image format:</label>
          <select v-model="exportSettings.imageFormat" class="select-input">
            <option value="jpeg">JPEG (smaller file)</option>
            <option value="png">PNG (lossless)</option>
          </select>
        </div>

        <div v-if="exportSettings.imageFormat === 'jpeg'" class="input-group">
          <label>JPEG quality:</label>
          <input
            type="number"
            v-model.number="exportSettings.jpegQuality"
            min="1"
            max="100"
            class="number-input"
          />
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="dialog-actions">
        <button @click="close" class="btn btn-secondary">Cancel</button>
        <button @click="exportPdf" class="btn btn-primary" :disabled="isExporting">
          {{ isExporting ? 'Exporting...' : '🚀 Export PDF' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePdfStore } from '~/stores/pdf'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const pdfStore = usePdfStore()
const isExporting = ref(false)

const pageSizes: Record<string, [number, number]> = {
  letter: [8.5, 11.0],
  'letter-landscape': [11.0, 8.5],
  a4: [8.27, 11.69],
  'a4-landscape': [11.69, 8.27],
  legal: [8.5, 14.0],
  tabloid: [11.0, 17.0],
  a3: [11.69, 16.54]
}

const exportSettings = ref({
  pageSize: '',
  padToExactSize: false,
  firstOddPage: 1,
  twoUpEnabled: false,
  verticalAlign: 'top',
  layoutMode: 'sequential',
  startPage: 1,
  addPageNumbers: false,
  pageNumberFormat: 'Page {n}',
  pageNumberSize: 11,
  pageNumberMargin: 30,
  dpi: 300,
  imageFormat: 'jpeg',
  jpegQuality: 95
})

const close = () => {
  emit('close')
}

const exportPdf = async () => {
  if (!pdfStore.pdfInfo || isExporting.value) return

  isExporting.value = true

  // Show progress overlay
  pdfStore.isLoading = true
  pdfStore.loadingMessage = 'Preparing export...'
  pdfStore.loadingProgress = null

  try {
    // Prepare page filters
    const pageFilters: Record<number, any> = {}
    pdfStore.pageFilters.forEach((filters, pageNum) => {
      pageFilters[pageNum] = filters
    })

    // Prepare export request
    const exportData = {
      dpi: exportSettings.value.dpi,
      page_filters: pageFilters,
      image_format: exportSettings.value.imageFormat,
      jpeg_quality: exportSettings.value.jpegQuality,
      target_page_size: exportSettings.value.pageSize ? pageSizes[exportSettings.value.pageSize] : null,
      pad_to_exact_size: exportSettings.value.padToExactSize,
      first_odd_page: exportSettings.value.firstOddPage,
      two_up_enabled: exportSettings.value.twoUpEnabled,
      layout_mode: exportSettings.value.layoutMode,
      vertical_align: exportSettings.value.verticalAlign,
      start_page: exportSettings.value.startPage,
      add_page_numbers: exportSettings.value.addPageNumbers,
      page_number_format: exportSettings.value.pageNumberFormat,
      page_number_size: exportSettings.value.pageNumberSize,
      page_number_margin: exportSettings.value.pageNumberMargin
    }

    // Update progress
    pdfStore.loadingMessage = 'Generating PDF...'
    pdfStore.loadingProgress = 20

    // Download the exported PDF
    const response = await fetch(`/api/pdf/${pdfStore.pdfInfo.pdf_id}/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(exportData)
    })

    if (!response.ok) {
      throw new Error('Export failed')
    }

    pdfStore.loadingMessage = 'Downloading...'
    pdfStore.loadingProgress = 80

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `processed_${pdfStore.pdfInfo.filename}`
    a.click()
    URL.revokeObjectURL(url)

    pdfStore.loadingProgress = 100
    await new Promise(resolve => setTimeout(resolve, 200)) // Brief pause to show completion

    close()
  } catch (error) {
    console.error('Export failed:', error)
    alert('Export failed. Please try again.')
  } finally {
    isExporting.value = false
    pdfStore.isLoading = false
    pdfStore.loadingMessage = ''
    pdfStore.loadingProgress = null
  }
}
</script>

<style scoped>
.export-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.export-dialog {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.export-dialog h2 {
  margin-bottom: 1.5rem;
  color: #1d1d1f;
}

.export-section {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e5e5e7;
}

.export-section:last-of-type {
  border-bottom: none;
}

.export-section h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #1d1d1f;
}

.select-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #d2d2d7;
  border-radius: 6px;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.input-group label {
  font-size: 0.875rem;
  color: #86868b;
  min-width: 120px;
}

.number-input {
  width: 80px;
  padding: 0.25rem 0.5rem;
  border: 1px solid #d2d2d7;
  border-radius: 4px;
  font-size: 0.875rem;
}

.info-text {
  font-size: 0.75rem;
  color: #86868b;
  margin-top: 0.5rem;
}

.page-number-options {
  margin-left: 1.5rem;
  margin-top: 0.5rem;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #007aff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0051d5;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f5f5f7;
  color: #1d1d1f;
  border: 1px solid #d2d2d7;
}

.btn-secondary:hover {
  background: #e5e5e7;
}
</style>