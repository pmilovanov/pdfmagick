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

      // Check if already loaded
      if (this.originalImages.has(pageNum)) {
        // Page already loaded, check if we have the processed version
        if (!this.processedImages.has(pageNum)) {
          // Only apply filters if they're non-default
          const filters = this.pageFilters.get(pageNum)
          if (filters && JSON.stringify(filters) !== JSON.stringify(this.getDefaultFilters())) {
            await this.applyFilters(pageNum, filters)
          } else {
            // Use original as processed for default filters
            const originalUrl = this.originalImages.get(pageNum)
            if (originalUrl) {
              this.processedImages.set(pageNum, originalUrl)
            }
          }
        }
        return
      }

      // Load new page
      this.isLoading = true
      try {
        // Load original image
        const originalUrl = `/api/pdf/${this.pdfInfo.pdf_id}/page/${pageNum}/render?dpi=150&format=webp&quality=85`
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
      } finally {
        this.isLoading = false
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
        const response = await $fetch(`/api/pdf/${this.pdfInfo.pdf_id}/page/${pageNum}/filter`, {
          method: 'POST',
          body: {
            filters,
            dpi: 150,
            format: 'webp',
            quality: 85
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

        // Only load page if not already loaded
        if (!this.originalImages.has(pageNum)) {
          this.loadPage(pageNum)
        }

        // Preload adjacent pages in background for smoother navigation
        this.preloadAdjacentPages(pageNum)
      }
    },

    preloadAdjacentPages(currentPage: number) {
      if (!this.pdfInfo) return

      // Preload next and previous pages in background
      const pagesToPreload = [currentPage - 1, currentPage + 1]

      pagesToPreload.forEach(pageNum => {
        if (pageNum >= 0 && pageNum < this.pdfInfo!.page_count && !this.originalImages.has(pageNum)) {
          // Load in background without blocking
          setTimeout(() => {
            if (!this.originalImages.has(pageNum)) {
              const originalUrl = `/api/pdf/${this.pdfInfo!.pdf_id}/page/${pageNum}/render?dpi=150&format=webp&quality=85`
              this.originalImages.set(pageNum, originalUrl)

              // If page has no custom filters, set processed same as original
              if (!this.pageFilters.has(pageNum)) {
                this.processedImages.set(pageNum, originalUrl)
              }
            }
          }, 100)
        }
      })
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