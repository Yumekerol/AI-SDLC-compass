<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import NotificationPanel from '@/components/notifications/NotificationPanel.vue'

const router = useRouter()
const notifStore = useNotificationsStore()
const notifWrapperRef = ref<HTMLElement | null>(null)

function goHome() {
  router.push('/')
}

function handleOutsideClick(event: MouseEvent) {
  if (notifStore.isOpen && notifWrapperRef.value && !notifWrapperRef.value.contains(event.target as Node)) {
    notifStore.closePanel()
  }
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
})
</script>

<template>
  <header class="app-header">
    <div class="header-inner container">
      <!-- Left: Logo & Proof of Concept tag -->
      <div class="brand-group" @click="goHome" role="button" tabindex="0" @keydown.enter="goHome">
        <div class="logo-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="24" height="24" rx="6" fill="#6D3CC8" />
            <circle cx="12" cy="12" r="7" stroke="#FFFFFF" stroke-width="2" />
            <polygon points="12,7 14.5,12 12,11" fill="#FFFFFF" />
            <polygon points="12,17 9.5,12 12,13" fill="#A5B4FC" />
          </svg>
        </div>
        <div class="brand-text">
          <span class="app-title">AI-SDLC Compass</span>
          <span class="badge badge-poc">PROOF OF CONCEPT</span>
        </div>
      </div>

      <!-- Right: Delivery workspace, Team profile avatar & Notifications -->
      <div class="workspace-profile">
        <span class="workspace-label">Delivery workspace</span>

        <!-- Notifications Bell & Dropdown -->
        <div ref="notifWrapperRef" class="notifications-wrapper">
          <button
            type="button"
            class="notif-bell-btn"
            :class="{ 'is-active': notifStore.isOpen }"
            aria-label="View notifications"
            :aria-expanded="notifStore.isOpen"
            @click="notifStore.togglePanel"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="bell-svg"
              aria-hidden="true"
            >
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
            <span v-if="notifStore.unreadCount > 0" class="bell-badge">
              {{ notifStore.unreadCount }}
            </span>
          </button>

          <!-- Dropdown Panel -->
          <NotificationPanel v-if="notifStore.isOpen" />
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: var(--header-height);
  background-color: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 40;
}

.header-inner {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  user-select: none;
}

.logo-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.brand-text {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.app-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.workspace-profile {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.workspace-label {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.avatar-circle {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

/* Notifications Button & Badge */
.notifications-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.notif-bell-btn {
  position: relative;
  width: 36px;
  height: 36px;
  min-width: 36px;
  min-height: 36px;
  padding: 0;
  border-radius: var(--radius-full);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary, #475569);
  cursor: pointer;
  transition: all 0.15s ease;
  line-height: 1;
}

.notif-bell-btn:hover,
.notif-bell-btn.is-active {
  background-color: var(--color-surface-hover);
  color: var(--color-primary);
  border-color: var(--color-primary-border);
}

.bell-svg {
  width: 18px;
  height: 18px;
  display: block;
  flex-shrink: 0;
  color: inherit;
}

.bell-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background-color: var(--color-primary);
  color: #ffffff;
  font-size: 0.6875rem;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  border: 2px solid var(--color-surface);
  line-height: 1;
}

@media (max-width: 640px) {
  .workspace-label {
    display: none;
  }
  .user-name {
    display: none;
  }
}
</style>
