// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: [
    '@pinia/nuxt',
    '@vueuse/nuxt'
  ],
  css: [
    // Removing PrimeVue CSS for now to simplify
  ],
  build: {
    transpile: ['primevue']
  },
  nitro: {
    devProxy: {
      '/api': {
        target: 'http://localhost:8000/api',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000/ws',
        ws: true,
        changeOrigin: true
      }
    }
  },
  typescript: {
    strict: true
  }
})