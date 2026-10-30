<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import type { AppNotification } from '@/types'

const router = useRouter()
const store = useNotificationsStore()

function open(item: AppNotification) {
  store.dismissToast(item.id)
  store.markAsRead(item.id)
  if (item.route_hint) router.push(item.route_hint)
}
</script>

<template>
  <div class="toast-stack" aria-live="polite">
    <div
      v-for="item in store.toasts"
      :key="item.id"
      class="toast"
      :class="`toast-${item.level || 'info'}`"
      role="status"
    >
      <button type="button" class="toast-body" @click="open(item)">
        <span class="toast-title">{{ item.title }}</span>
        <span class="toast-message">{{ item.message }}</span>
        <span v-if="item.route_hint" class="toast-action">Open →</span>
      </button>
      <button type="button" class="toast-close" aria-label="Dismiss" @click="store.dismissToast(item.id)">×</button>
    </div>
  </div>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  right: 1.25rem;
  bottom: 1.25rem;
  z-index: 120;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: min(360px, calc(100vw - 2rem));
}

.toast {
  display: flex;
  align-items: flex-start;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--color-primary);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  animation: slideIn 0.2s ease-out;
}

.toast-success {
  border-left-color: #16a34a;
}

.toast-warning {
  border-left-color: #d97706;
}

.toast-error {
  border-left-color: #dc2626;
}

.toast-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.75rem 0.875rem;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  min-height: auto;
}

.toast-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.toast-message {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.toast-action {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-top: 0.125rem;
}

.toast-close {
  background: none;
  border: none;
  font-size: 1.125rem;
  line-height: 1;
  color: var(--color-text-muted);
  padding: 0.625rem 0.75rem;
  cursor: pointer;
  min-height: auto;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
