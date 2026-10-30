import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { AppNotification } from '@/types'
import * as api from '@/api'
import router from '@/router'
import { useSessionStore } from './session'

const POLL_INTERVAL_MS = 5000
const TOAST_DURATION_MS = 8000

export const useNotificationsStore = defineStore('notifications', () => {
  const sessionStore = useSessionStore()
  const notifications = ref<AppNotification[]>([])
  const isOpen = ref(false)
  const isLoading = ref(false)
  /** Newly arrived notifications, shown briefly as toasts. */
  const toasts = ref<AppNotification[]>([])

  // Notifications already known for this session. The first fetch for a
  // session only fills this in, so reloading the page doesn't re-toast
  // everything that happened before.
  let seenIds = new Set<string>()
  let seeded = false
  let pollTimer: ReturnType<typeof setInterval> | null = null

  const unreadCount = computed(() => {
    return notifications.value.filter((n) => !n.read).length
  })

  const hasUnread = computed(() => unreadCount.value > 0)

  function togglePanel() {
    isOpen.value = !isOpen.value
  }

  function closePanel() {
    isOpen.value = false
  }

  function openPanel() {
    isOpen.value = true
  }

  function showToast(item: AppNotification) {
    // Skip it if the user is already looking at the page it points to.
    if (item.route_hint && router.currentRoute.value.path === item.route_hint) return
    toasts.value.push(item)
    setTimeout(() => dismissToast(item.id), TOAST_DURATION_MS)
  }

  function dismissToast(id: string) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  async function fetchNotifications() {
    try {
      isLoading.value = true
      const data = await api.fetchNotifications(sessionStore.sessionId || undefined)
      notifications.value = data
      for (const item of data) {
        if (seenIds.has(item.id)) continue
        seenIds.add(item.id)
        if (seeded && !item.read) showToast(item)
      }
      seeded = true
    } catch (err) {
      console.warn('Failed to fetch notifications:', err)
    } finally {
      isLoading.value = false
    }
  }

  /** Keep the bell current while the app is open. Cheap: one small GET per
   *  interval, and only once a backend session exists. */
  function startPolling() {
    if (pollTimer) return
    void fetchNotifications()
    if (api.USE_MOCKS) return
    pollTimer = setInterval(() => {
      if (sessionStore.sessionId) void fetchNotifications()
    }, POLL_INTERVAL_MS)
  }

  // Arriving on the page a toast points to makes that toast redundant.
  router.afterEach((to) => {
    toasts.value = toasts.value.filter((t) => t.route_hint !== to.path)
  })

  watch(
    () => sessionStore.sessionId,
    () => {
      seenIds = new Set()
      seeded = false
      notifications.value = []
      toasts.value = []
      void fetchNotifications()
    }
  )

  async function markAsRead(id: string) {
    const item = notifications.value.find((n) => n.id === id)
    if (item && !item.read) {
      item.read = true
      try {
        await api.markNotificationAsRead(id, sessionStore.sessionId || undefined)
      } catch (err) {
        console.warn('Failed to mark notification as read:', err)
      }
    }
  }

  async function markAllAsRead() {
    notifications.value.forEach((n) => {
      n.read = true
    })
    try {
      await api.markAllNotificationsAsRead(sessionStore.sessionId || undefined)
    } catch (err) {
      console.warn('Failed to mark all notifications as read:', err)
    }
  }

  async function clearAll() {
    notifications.value = []
    try {
      await api.clearAllNotifications(sessionStore.sessionId || undefined)
    } catch (err) {
      console.warn('Failed to clear notifications:', err)
    }
  }

  async function deleteNotification(id: string) {
    notifications.value = notifications.value.filter((n) => n.id !== id)
    try {
      await api.deleteNotification(id, sessionStore.sessionId || undefined)
    } catch (err) {
      console.warn('Failed to delete notification:', err)
    }
  }

  return {
    notifications,
    isOpen,
    isLoading,
    toasts,
    unreadCount,
    hasUnread,
    togglePanel,
    closePanel,
    openPanel,
    fetchNotifications,
    startPolling,
    dismissToast,
    markAsRead,
    markAllAsRead,
    clearAll,
    deleteNotification
  }
})
