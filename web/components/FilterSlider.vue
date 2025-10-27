<template>
  <div class="filter-slider">
    <div class="slider-header">
      <label class="slider-label">{{ label }}</label>
      <input
        type="number"
        :value="modelValue"
        @input="updateValue($event.target.value)"
        :min="min"
        :max="max"
        :step="step"
        class="slider-input"
      />
    </div>
    <input
      type="range"
      :value="modelValue"
      @input="updateValue($event.target.value)"
      :min="min"
      :max="max"
      :step="step"
      class="slider"
    />
  </div>
</template>

<script setup lang="ts">
interface Props {
  label: string
  modelValue: number
  min?: number
  max?: number
  step?: number
}

const props = withDefaults(defineProps<Props>(), {
  min: 0,
  max: 100,
  step: 1
})

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const updateValue = (value: string | number) => {
  emit('update:modelValue', Number(value))
}
</script>

<style scoped>
.filter-slider {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.slider-label {
  font-size: 0.875rem;
  color: #1d1d1f;
}

.slider-input {
  width: 60px;
  padding: 0.25rem 0.5rem;
  border: 1px solid #d2d2d7;
  border-radius: 4px;
  font-size: 0.75rem;
  text-align: right;
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
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #007aff;
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #007aff;
  cursor: pointer;
}
</style>