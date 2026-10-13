<script setup lang="ts">
import type { AppError } from '@/types'

defineProps<{
  error: AppError
}>()

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'dismiss'): void
}>()
</script>

<template>
  <div
    class="error-banner"
    :class="`error-type-${error.type}`"
    role="alert"
    aria-live="assertive"
  >
    <div class="error-icon" aria-hidden="true">
      <!-- Out of scope icon -->
      <svg v-if="error.type === 'out_of_scope'" viewBox="0 0 20 20" fill="currentColor">
        <path
          fill-rule="evenodd"
          d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 5Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
          clip-rule="evenodd"
        />
      </svg>
      <!-- Network / generic error icon -->
      <svg v-else viewBox="0 0 20 20" fill="currentColor">
        <path
          fill-rule="evenodd"
          d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM8.28 7.22a.75.75 0 0 0-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 1 0 1.06 1.06L10 11.06l1.72 1.72a.75.75 0 1 0 1.06-1.06L11.06 10l1.72-1.72a.75.75 0 0 0-1.06-1.06L10 8.94 8.28 7.22Z"
          clip-rule="evenodd"
        />
      </svg>
    </div>

    <div class="error-body">
      <h3 class="error-title">{{ error.title }}</h3>
      <p class="error-message">{{ error.message }}</p>
      <p v-if="error.details" class="error-details">{{ error.details }}</p>
    </div>

    <div class="error-actions">
      <button
        v-if="error.canRetry"
        type="button"
        class="btn-retry"
        @click="emit('retry')"
      >
        <svg class="retry-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M13.836 2.477a.75.75 0 0 1 .75.75v3.182a.75.75 0 0 1-.75.75h-3.182a.75.75 0 0 1 0-1.5h1.861a5.5 5.5 0 1 0 1.025 5.09.75.75 0 0 1 1.439.426 7 7 0 1 1-1.328-6.448h1.435a.75.75 0 0 1 .75-.75Z"
            clip-rule="evenodd"
          />
        </svg>
        <span>{{ error.retryActionName || 'Retry' }}</span>
      </button>

      <button
        type="button"
        class="btn-dismiss"
        aria-label="Dismiss error"
        @click="emit('dismiss')"
      >
        &times;
      </button>
    </div>
  </div>
</template>

<style scoped>
.error-banner {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-radius: var(--radius-md);
  margin: 1.25rem 0;
  border: 1px solid transparent;
  animation: slideDown 0.2s ease-out;
}

.error-type-out_of_scope {
  background-color: var(--color-warning-bg);
  border-color: var(--color-warning-border);
  color: var(--color-warning-text);
}

.error-type-network,
.error-type-ai_down {
  background-color: var(--color-danger-bg);
  border-color: var(--color-danger-border);
  color: var(--color-danger-text);
}

.error-icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  margin-top: 2px;
}

.error-icon svg {
  width: 100%;
  height: 100%;
}

.error-body {
  flex: 1;
}

.error-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: inherit;
  margin-bottom: 0.25rem;
}

.error-message {
  font-size: 0.875rem;
  color: inherit;
  opacity: 0.95;
  line-height: 1.4;
}

.error-details {
  font-size: 0.8125rem;
  margin-top: 0.375rem;
  opacity: 0.8;
}

.error-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-retry {
  min-height: var(--min-touch-target);
  padding: 0.5rem 1rem;
  background-color: #ffffff;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.btn-retry:hover {
  background-color: var(--color-surface-hover);
}

.retry-icon {
  width: 14px;
  height: 14px;
}

.btn-dismiss {
  width: var(--min-touch-target);
  height: var(--min-touch-target);
  padding: 0;
  background: transparent;
  border: none;
  font-size: 1.25rem;
  color: inherit;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
