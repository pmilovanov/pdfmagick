<template>
  <Transition name="fade">
    <div v-if="visible" class="progress-overlay">
      <div class="progress-content">
        <div class="progress-spinner"></div>
        <h3>{{ title }}</h3>
        <p v-if="message">{{ message }}</p>
        <div v-if="progress !== null" class="progress-bar">
          <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
        </div>
        <p v-if="progress !== null" class="progress-text">{{ Math.round(progress) }}%</p>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
interface Props {
  visible: boolean
  title?: string
  message?: string
  progress?: number | null
}

withDefaults(defineProps<Props>(), {
  title: 'Processing...',
  message: '',
  progress: null
})
</script>

<style scoped>
.progress-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.progress-content {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  min-width: 300px;
  max-width: 400px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.progress-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #007aff;
  border-radius: 50%;
  margin: 0 auto 1rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.progress-content h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  color: #1d1d1f;
}

.progress-content p {
  margin: 0 0 1rem 0;
  color: #86868b;
  font-size: 0.875rem;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: #f3f3f3;
  border-radius: 3px;
  overflow: hidden;
  margin: 1rem 0 0.5rem;
}

.progress-fill {
  height: 100%;
  background: #007aff;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.875rem;
  color: #007aff;
  font-weight: 600;
  margin: 0;
}

/* Transition classes */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>