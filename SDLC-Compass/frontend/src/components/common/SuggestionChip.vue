<script setup lang="ts">
defineProps<{
  label: string
  selected?: boolean
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'select'): void
}>()
</script>

<template>
  <button
    type="button"
    class="suggestion-chip"
    :class="{ 'chip-selected': selected }"
    :disabled="disabled"
    @click="emit('select')"
  >
    <span class="chip-text">{{ label }}</span>
  </button>
</template>

<style scoped>
.suggestion-chip {
  min-height: var(--min-touch-target);
  padding: 0.5rem 1rem;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  color: var(--color-text-primary);
  font-size: 0.875rem;
  font-weight: 500;
  text-align: left;
  line-height: 1.35;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  display: inline-flex;
  align-items: center;
  box-shadow: var(--shadow-sm);
}

.suggestion-chip:hover:not(:disabled) {
  border-color: var(--color-primary);
  background-color: var(--color-primary-light);
  color: var(--color-primary);
}

.chip-selected {
  background-color: var(--color-primary-light);
  border-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 600;
}

.suggestion-chip:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .suggestion-chip {
    width: 100%;
  }
}
</style>
