<script setup lang="ts">
defineProps<{
  message?: string
}>()
</script>

<template>
  <div class="loading-overlay" role="status" aria-live="polite">
    <div class="loading-modal">
      <div class="spinner-ring" aria-hidden="true"></div>
      <p class="loading-message">{{ message || 'Loading...' }}</p>
      <span class="sr-only">Processing request</span>
    </div>
  </div>
</template>

<style scoped>
.loading-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: fadeIn 0.15s ease-out;
}

.loading-modal {
  background-color: var(--color-surface);
  padding: 2rem 2.5rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  max-width: 420px;
  text-align: center;
}

.spinner-ring {
  width: 44px;
  height: 44px;
  border: 3px solid var(--color-primary-light);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-message {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
