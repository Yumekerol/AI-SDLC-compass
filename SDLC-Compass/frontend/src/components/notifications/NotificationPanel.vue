<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import type { AppNotification } from '@/types'

const router = useRouter()
const store = useNotificationsStore()

function formatRelativeTime(dateStr: string): string {
  try {
    const timestamp = new Date(dateStr).getTime()
    if (isNaN(timestamp)) return ''
    const diffSeconds = Math.floor((Date.now() - timestamp) / 1000)

    if (diffSeconds < 60) return 'Just now'
    const diffMinutes = Math.floor(diffSeconds / 60)
    if (diffMinutes < 60) return `${diffMinutes} min ago`
    const diffHours = Math.floor(diffMinutes / 60)
    if (diffHours < 24) return `${diffHours} h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays} d ago`
  } catch {
    return ''
  }
}

function handleNotificationClick(item: AppNotification) {
  store.markAsRead(item.id)
  if (item.route_hint) {
    store.closePanel()
    router.push(item.route_hint)
  }
}

function handleActionClick(item: AppNotification, event: MouseEvent) {
  event.stopPropagation()
  store.markAsRead(item.id)
  if (item.route_hint) {
    store.closePanel()
    router.push(item.route_hint)
  }
}

function handleDismissClick(item: AppNotification, event: MouseEvent) {
  event.stopPropagation()
  store.deleteNotification(item.id)
}

function getActionLabel(item: AppNotification): string {
  if (item.action_label) return item.action_label
  if (item.type === 'report_ready') return 'See report →'
  if (item.type === 'specialist_question') return 'Answer →'
  if (item.type === 'agents_failed') return 'Open conversation →'
  if (item.type === 'scan_failed') return 'See evidence →'
  if (item.type === 'scan_complete') return 'Review signals →'
  return 'View details →'
}
</script>

<template>
  <div class="notifications-panel" role="region" aria-label="Notifications panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="panel-title-group">
        <span class="panel-title">Notifications</span>
        <span v-if="store.unreadCount > 0" class="unread-pill">{{ store.unreadCount }}</span>
      </div>
      <div v-if="store.notifications.length > 0" class="header-actions">
        <button
          v-if="store.unreadCount > 0"
          type="button"
          class="header-action-btn"
          @click="store.markAllAsRead"
        >
          Mark all as read
        </button>
        <span v-if="store.unreadCount > 0" class="action-divider">·</span>
        <button
          type="button"
          class="header-action-btn clear-btn"
          @click="store.clearAll"
        >
          Clear all
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="store.notifications.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
      </div>
      <p class="empty-title">All caught up</p>
      <p class="empty-subtitle">You have no new notifications right now.</p>
    </div>

    <!-- Notifications List -->
    <div v-else class="notifications-list">
      <article
        v-for="item in store.notifications"
        :key="item.id"
        class="notification-card"
        :class="[
          `level-${item.level || 'info'}`,
          { 'is-unread': !item.read }
        ]"
        tabindex="0"
        role="button"
        @click="handleNotificationClick(item)"
        @keydown.enter="handleNotificationClick(item)"
      >
        <!-- Top row: Icon + Title + Timestamp & Unread dot & Dismiss -->
        <div class="card-top-row">
          <div class="icon-badge" :class="`badge-${item.level || 'info'}`" aria-hidden="true">
            <!-- Success / Complete Checkmark -->
            <svg
              v-if="item.level === 'success' || item.type === 'report_ready' || item.type === 'scan_complete'"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clip-rule="evenodd"
              />
            </svg>

            <!-- Warning Triangle -->
            <svg
              v-else-if="item.level === 'warning' || item.type === 'specialist_question'"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clip-rule="evenodd"
              />
            </svg>

            <!-- Error / Danger Circle -->
            <svg
              v-else-if="item.level === 'error' || item.type === 'scan_failed'"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clip-rule="evenodd"
              />
            </svg>

            <!-- Info (Default) -->
            <svg v-else viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clip-rule="evenodd"
              />
            </svg>
          </div>

          <div class="title-wrap">
            <h4 class="card-title">{{ item.title }}</h4>
          </div>

          <div class="card-meta">
            <span class="card-time">{{ formatRelativeTime(item.created_at) }}</span>
            <span v-if="!item.read" class="unread-dot" title="Unread notification" />
            <button
              type="button"
              class="card-dismiss-btn"
              title="Dismiss notification"
              aria-label="Dismiss notification"
              @click="handleDismissClick(item, $event)"
            >
              <svg viewBox="0 0 16 16" fill="currentColor">
                <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Middle: Description Message -->
        <p class="card-message">{{ item.message }}</p>

        <!-- Bottom: Domain Tag & Quick Action Link -->
        <div class="card-bottom-row">
          <span v-if="item.domain" class="domain-pill">
            {{ item.domain }}
          </span>
          <span v-else />

          <button
            v-if="item.route_hint"
            type="button"
            class="action-link"
            @click="handleActionClick(item, $event)"
          >
            {{ getActionLabel(item) }}
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.notifications-panel {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 390px;
  max-width: calc(100vw - 32px);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: 0 12px 30px -4px rgba(15, 23, 42, 0.12), 0 4px 12px -2px rgba(15, 23, 42, 0.08);
  padding: 1rem;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  animation: fadeInDown 0.18s ease-out;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border-subtle);
}

.panel-title-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.panel-title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.unread-pill {
  font-size: 0.6875rem;
  font-weight: 700;
  background-color: var(--color-primary-subtle);
  color: var(--color-primary);
  padding: 0.125rem 0.4375rem;
  border-radius: var(--radius-full);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-action-btn {
  background: none;
  border: none;
  padding: 0;
  min-height: unset;
  min-width: unset;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  transition: opacity 0.15s ease, color 0.15s ease;
}

.header-action-btn:hover {
  text-decoration: underline;
}

.header-action-btn.clear-btn {
  color: var(--color-text-muted);
}

.header-action-btn.clear-btn:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
}

.action-divider {
  font-size: 0.75rem;
  color: var(--color-border-strong);
  user-select: none;
}

.notifications-list {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  max-height: 480px;
  overflow-y: auto;
  padding-right: 0.25rem;
}

/* Custom scrollbar */
.notifications-list::-webkit-scrollbar {
  width: 5px;
}
.notifications-list::-webkit-scrollbar-thumb {
  background-color: var(--color-border);
  border-radius: 4px;
}

.notification-card {
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-md);
  padding: 0.75rem 0.875rem;
  border: 1px solid var(--color-border);
  background-color: #ffffff;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, transform 0.1s ease;
  user-select: none;
  position: relative;
}

.notification-card:hover {
  transform: translateY(-1px);
}

/* Level color variations */
.notification-card.level-success {
  background-color: #f7fdfa;
  border-color: #d1fae5;
}
.notification-card.level-warning {
  background-color: #fffef8;
  border-color: #fef3c7;
}
.notification-card.level-error {
  background-color: #fffaf9;
  border-color: #fee2e2;
}
.notification-card.level-info {
  background-color: #faf8ff;
  border-color: #ede9fe;
}

.notification-card.is-unread {
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
}

.card-top-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.icon-badge {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
}

.icon-badge svg {
  width: 20px;
  height: 20px;
}

.icon-badge.badge-success {
  color: #059669;
}
.icon-badge.badge-warning {
  color: #d97706;
}
.icon-badge.badge-error {
  color: #dc2626;
}
.icon-badge.badge-info {
  color: var(--color-primary);
}

.title-wrap {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-shrink: 0;
}

.card-time {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
}

.unread-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: #047857;
  display: inline-block;
}

.card-dismiss-btn {
  background: none;
  border: none;
  padding: 2px;
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  border-radius: var(--radius-sm);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, color 0.15s ease, background-color 0.15s ease;
  min-height: unset;
  min-width: unset;
}

.card-dismiss-btn svg {
  width: 12px;
  height: 12px;
}

.notification-card:hover .card-dismiss-btn {
  opacity: 0.7;
}

.card-dismiss-btn:hover {
  opacity: 1 !important;
  color: var(--color-text-primary);
  background-color: rgba(0, 0, 0, 0.06);
}

.card-message {
  font-size: 0.75rem;
  line-height: 1.45;
  color: var(--color-text-secondary);
  margin: 0.375rem 0 0.5rem 2rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-bottom-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-left: 2rem;
}

.domain-pill {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--color-text-muted);
  background-color: rgba(0, 0, 0, 0.04);
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-sm);
  letter-spacing: 0.01em;
}

.action-link {
  background: none;
  border: none;
  padding: 0;
  min-height: unset;
  min-width: unset;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  transition: transform 0.1s ease;
}

.action-link:hover {
  text-decoration: underline;
  transform: translateX(1px);
}

/* Empty State */
.empty-state {
  padding: 2rem 1rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.empty-icon {
  width: 40px;
  height: 40px;
  color: var(--color-text-muted);
  opacity: 0.5;
  margin-bottom: 0.25rem;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.empty-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin: 0;
}
</style>
