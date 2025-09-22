import { defineStore } from 'pinia'

export interface FilterSettings {
  brightness: number
  contrast: number
  highlights: number
  midtones: number
  shadows: number
  exposure: number
  saturation: number
  vibrance: number
  sharpness: number
  black_point: number
  white_point: number
  gamma: number
}

export interface PDFInfo {
  pdf_id: string
  filename: string
  page_count: number
  page_dimensions: Array<{
    width: number
    height: number
    width_inches: number
    height_inches: number
  }>
}

export const usePdfStore = defineStore('pdf', {
  state: () => ({
    pdfInfo: null as PDFInfo | null,
    currentPage: 0,
    pageFilters: new Map<number, FilterSettings>(),
    originalImages: new Map<number, string>(),
    processedImages: new Map<number, string>(),
    isLoading: false,
    loadingMessage: '',
    loadingProgress: null as number | null,
    wsConnection: null as WebSocket | null
  }),

  getters: {
    currentPageFilters(): FilterSettings {
      return this.pageFilters.get(this.currentPage) || this.getDefaultFilters()
    },
    hasFilters(): boolean {
      return this.pageFilters.size > 0
    },
    effectiveDpi(): number {
      // Calculate effective DPI for current page to avoid huge images
      if (!this.pdfInfo || this.currentPage >= this.pdfInfo.page_dimensions.length) {
        return 150
      }

      const pageDim = this.pdfInfo.page_dimensions[this.currentPage]
      const maxDimension = Math.max(pageDim.width_inches, pageDim.height_inches)

      // Scale down DPI for very large pages to keep preview manageable
      // Target max dimension of ~2000px for preview
      if (maxDimension > 13.3) {  // Would be >2000px at 150 DPI
        return Math.floor(2000 / maxDimension)
      }

      return 150
    }
  },

  actions: {
    getDefaultFilters(): FilterSettings {
      return {
        brightness: 0,
        contrast: 0,
        highlights: 0,
        midtones: 0,
        shadows: 0,
        exposure: 0,
        saturation: 0,
        vibrance: 0,
        sharpness: 0,
        black_point: 0,
        white_point: 255,
        gamma: 1.0
      }
    },

    async uploadPdf(file: File) {
      this.isLoading = true
      try {
        const formData = new FormData()
        formData.append('file', file)

        const response = await $fetch<PDFInfo>('/api/pdf/upload', {
          method: 'POST',
          body: formData
        })

        this.pdfInfo = response
        this.currentPage = 0
        this.pageFilters.clear()
        this.originalImages.clear()
        this.processedImages.clear()

        // Load first page
        await this.loadPage(0)
      } finally {
        this.isLoading = false
      }
    },

    async loadPage(pageNum: number) {
      if (!this.pdfInfo) return

      const startTime = performance.now()

      // Don't show loading spinner for page switches
      try {
        // Calculate DPI for preview (target ~700px tall for display)
        const pageDim = this.pdfInfo.page_dimensions[pageNum]
        const targetHeight = 700  // pixels for preview
        const dpi = Math.min(Math.floor(targetHeight / pageDim.height_inches), 100)  // Cap at 100 DPI for previews

        // Build URL directly to FastAPI with lower quality for faster loading
        const originalUrl = `http://localhost:8000/api/pdf/${this.pdfInfo.pdf_id}/page/${pageNum}/render?dpi=${dpi}&format=jpeg&quality=70`

        // Just set the URL without preloading
        this.originalImages.set(pageNum, originalUrl)

        // Check if page has custom filters
        const filters = this.pageFilters.get(pageNum)
        if (filters && JSON.stringify(filters) !== JSON.stringify(this.getDefaultFilters())) {
          // Apply custom filters
          await this.applyFilters(pageNum, filters)
        } else {
          // Use original as processed for default filters
          this.processedImages.set(pageNum, originalUrl)
        }

        const totalTime = performance.now() - startTime
        console.log(`Page ${pageNum} total client time: ${totalTime.toFixed(0)}ms (DPI: ${dpi})`)
      } catch (error) {
        console.error('Failed to load page:', error)
      }
    },

    async applyFilters(pageNum: number, filters: FilterSettings) {
      if (!this.pdfInfo) return

      // Save filters
      this.pageFilters.set(pageNum, filters)

      // If filters are default, just use original
      if (JSON.stringify(filters) === JSON.stringify(this.getDefaultFilters())) {
        const originalUrl = this.originalImages.get(pageNum)
        if (originalUrl) {
          this.processedImages.set(pageNum, originalUrl)
        }
        return
      }

      // Apply filters via API
      try {
        // Calculate DPI for preview (target ~700px tall for display)
        const pageDim = this.pdfInfo.page_dimensions[pageNum]
        const targetHeight = 700  // pixels for preview
        const dpi = Math.min(Math.floor(targetHeight / pageDim.height_inches), 100)  // Cap at 100 DPI for previews

        const response = await $fetch(`/api/pdf/${this.pdfInfo.pdf_id}/page/${pageNum}/filter`, {
          method: 'POST',
          body: {
            filters,
            dpi,
            format: 'jpeg',
            quality: 70
          }
        })

        // The response is a blob, convert to URL
        const blob = response as Blob
        const url = URL.createObjectURL(blob)
        this.processedImages.set(pageNum, url)
      } catch (error) {
        console.error('Failed to apply filters:', error)
      }
    },

    setCurrentPage(pageNum: number) {
      if (pageNum >= 0 && this.pdfInfo && pageNum < this.pdfInfo.page_count) {
        this.currentPage = pageNum
        // Load the page
        this.loadPage(pageNum)
      }
    },


    async copyFiltersToAllPages() {
      if (!this.pdfInfo) return

      const currentFilters = this.currentPageFilters
      for (let i = 0; i < this.pdfInfo.page_count; i++) {
        this.pageFilters.set(i, { ...currentFilters })
      }
    },

    async resetCurrentPage() {
      this.pageFilters.delete(this.currentPage)
      this.processedImages.delete(this.currentPage)

      // Reset to default and reload
      const defaultFilters = this.getDefaultFilters()
      await this.applyFilters(this.currentPage, defaultFilters)
    },

    resetAllPages() {
      this.pageFilters.clear()
      this.processedImages.clear()
      if (this.currentPage !== undefined) {
        this.loadPage(this.currentPage)
      }
    },

    async autoEnhanceAllPages() {
      if (!this.pdfInfo) return

      this.isLoading = true
      this.loadingMessage = 'Auto-enhancing all pages'
      this.loadingProgress = 0

      try {
        // Simple auto-enhance settings for all pages
        const enhancedFilters: FilterSettings = {
          ...this.getDefaultFilters(),
          contrast: 5,
          brightness: 2,
          black_point: 10,
          white_point: 245
        }

        const totalPages = this.pdfInfo.page_count

        // Apply to all pages with progress
        for (let i = 0; i < totalPages; i++) {
          this.pageFilters.set(i, { ...enhancedFilters })

          // Update progress
          this.loadingProgress = ((i + 1) / totalPages) * 100
          this.loadingMessage = `Enhancing page ${i + 1} of ${totalPages}`

          // Small delay to show progress only for multiple pages
          if (totalPages > 1) {
            await new Promise(resolve => setTimeout(resolve, 20))
          }
        }

        // Apply filters to current page after all settings are saved
        await this.applyFilters(this.currentPage, enhancedFilters)
      } finally {
        this.isLoading = false
        this.loadingMessage = ''
        this.loadingProgress = null
      }
    },

    initWebSocket() {
      const clientId = Math.random().toString(36).substring(7)
      this.wsConnection = new WebSocket(`ws://localhost:8000/ws/preview/${clientId}`)

      this.wsConnection.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'filter_complete' && data.page !== undefined) {
          // Update processed image
          this.processedImages.set(data.page, data.data.image_url)
        }
      }

      this.wsConnection.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    },

    closeWebSocket() {
      if (this.wsConnection) {
        this.wsConnection.close()
        this.wsConnection = null
      }
    }
  }
})