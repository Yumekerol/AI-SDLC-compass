<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = withDefaults(
  defineProps<{
    message?: string
    /** Offer "notify me when it's done" after this long. 0 disables it. */
    offerBackgroundAfterMs?: number
  }>(),
  { offerBackgroundAfterMs: 10_000 }
)

const emit = defineEmits<{ (e: 'background'): void }>()

const showOffer = ref(false)
const keepWaiting = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  if (props.offerBackgroundAfterMs > 0) {
    timer = setTimeout(() => (showOffer.value = true), props.offerBackgroundAfterMs)
  }
})

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>

<template>
  <div class="loading-overlay" role="status" aria-live="polite">
    <div class="loading-modal">
      <div class="spinner-ring" aria-hidden="true"></div>
      <p class="loading-message">{{ message || 'Loading...' }}</p>

      <div v-if="showOffer && !keepWaiting" class="background-offer">
        <p class="offer-text">This is taking a while. You can keep using the app and we'll notify you when it's done.</p>
        <div class="offer-actions">
          <button type="button" class="btn-primary" @click="emit('background')">Notify me when it's done</button>
          <button type="button" class="btn-secondary" @click="keepWaiting = true">Keep waiting</button>
        </div>
      </div>
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
  max-width: 440px;
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

.background-offer {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  border-top: 1px solid var(--color-border);
  padding-top: 1rem;
  animation: fadeIn 0.2s ease-out;
}

.offer-text {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

.offer-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  flex-wrap: wrap;
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
