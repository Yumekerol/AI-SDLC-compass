import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppNotification } from '@/types'
import * as api from '@/api'
import { useSessionStore } from './session'

export const useNotificationsStore = defineStore('notifications', () => {
  const sessionStore = useSessionStore()
  const notifications = ref<AppNotification[]>([])
  const isOpen = ref(false)
  const isLoading = ref(false)

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

  async function fetchNotifications() {
    try {
      isLoading.value = true
      const data = await api.fetchNotifications(sessionStore.sessionId || undefined)
      notifications.value = data
    } catch (err) {
      console.warn('Failed to fetch notifications:', err)
    } finally {
      isLoading.value = false
    }
  }

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

  // Initial load
  fetchNotifications()

  return {
    notifications,
    isOpen,
    isLoading,
    unreadCount,
    hasUnread,
    togglePanel,
    closePanel,
    openPanel,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    clearAll,
    deleteNotification
  }
})
