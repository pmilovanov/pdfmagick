<template>
  <div class="pdf-editor">
    <!-- Header -->
    <header class="editor-header">
      <h1>🎨 PDFMagick</h1>
      <div class="header-actions">
        <input
          type="file"
          ref="fileInput"
          @change="handleFileUpload"
          accept=".pdf"
          style="display: none"
        />
        <button @click="$refs.fileInput.click()" class="btn btn-primary">
          📄 Upload PDF
        </button>
        <button
          v-if="pdfStore.pdfInfo"
          @click="showExportDialog = true"
          class="btn btn-success"
        >
          💾 Export PDF
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <div v-if="pdfStore.pdfInfo" class="editor-main">
      <!-- Sidebar Controls -->
      <aside class="editor-sidebar">
        <PageNavigator />
        <FilterPanel />
      </aside>

      <!-- Image Comparison View -->
      <div class="editor-workspace">
        <ImageComparison />
      </div>
    </div>

    <!-- Welcome Screen -->
    <div v-else class="welcome-screen">
      <div class="welcome-content">
        <h2>Welcome to PDFMagick</h2>
        <p>Upload a PDF to begin processing</p>
        <button @click="$refs.fileInput.click()" class="btn btn-primary btn-lg">
          Choose PDF File
        </button>
      </div>
    </div>

    <!-- Export Dialog -->
    <ExportDialog
      :visible="showExportDialog"
      @close="showExportDialog = false"
    />

    <!-- Progress Overlay -->
    <ProgressOverlay
      :visible="pdfStore.isLoading"
      :title="pdfStore.loadingMessage || 'Processing...'"
      :progress="pdfStore.loadingProgress"
    />
  </div>
</template>

<script setup lang="ts">
import { usePdfStore } from '~/stores/pdf'
import ExportDialog from '~/components/ExportDialog.vue'
import ProgressOverlay from '~/components/ProgressOverlay.vue'

const pdfStore = usePdfStore()
const fileInput = ref<HTMLInputElement>()
const showExportDialog = ref(false)

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    await pdfStore.uploadPdf(file)
  }
}

onMounted(() => {
  pdfStore.initWebSocket()
})

onUnmounted(() => {
  pdfStore.closeWebSocket()
})
</script>

<style scoped>
.pdf-editor {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f7;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: white;
  border-bottom: 1px solid #e5e5e7;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.editor-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1d1d1f;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.editor-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.editor-sidebar {
  width: 320px;
  background: white;
  border-right: 1px solid #e5e5e7;
  overflow-y: auto;
}

.editor-workspace {
  flex: 1;
  padding: 2rem;
  overflow: auto;
}

.welcome-screen {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-content {
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
}

.welcome-content h2 {
  font-size: 2rem;
  margin-bottom: 1rem;
  color: #1d1d1f;
}

.welcome-content p {
  color: #86868b;
  margin-bottom: 2rem;
}

/* Button Styles */
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

.btn-primary:hover {
  background: #0051d5;
}

.btn-success {
  background: #34c759;
  color: white;
}

.btn-success:hover {
  background: #2ca048;
}

.btn-lg {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
}
</style>