import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/api'
import type { BackendConversationMessage, BackendPipelineProgress } from '@/api/types'
import type { UnresolvedKnowledgeGap } from '@/types/advisor'
import { mockConversation } from '@/mocks'
import { useSessionStore } from './session'

const POLL_INTERVAL_MS = 2000

export interface ChatEntry {
  id: string
  sender: 'agent' | 'user'
  agentInitial: string
  agentName: string
  text: string
  timestamp: string
}

function formatTime(iso: string | undefined): string {
  if (!iso) return ''
  const date = new Date(iso)
  return isNaN(date.getTime()) ? '' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function toChatEntry(m: BackendConversationMessage): ChatEntry {
  if (m.role === 'user') {
    return { id: m.id, sender: 'user', agentInitial: 'You', agentName: 'You', text: m.content, timestamp: formatTime(m.timestamp) }
  }
  const name = m.role === 'supervisor' ? 'Supervisor' : m.agent_label || 'Specialist'
  return {
    id: m.id,
    sender: 'agent',
    agentInitial: name.charAt(0).toUpperCase(),
    agentName: name,
    text: m.content,
    timestamp: formatTime(m.timestamp)
  }
}

function describeProgress(p: BackendPipelineProgress | null): string {
  if (!p) return 'The specialists are working…'
  switch (p.phase) {
    case 'starting':
      return 'Preparing the repository for the specialists…'
    case 'specialist':
      return `${p.current_label} is reviewing the repository (step ${p.step} of ${p.total_steps})…`
    case 'synthesizing':
      return 'All specialists are done. Writing the report…'
    case 'waiting_for_answer':
      return `${p.current_label} is waiting for your answer.`
    default:
      return 'The specialists are working…'
  }
}

/**
 * Step 3 conversation state. Lives in a store (not the view) so the polling
 * keeps going when the user navigates away — e.g. after choosing "notify me
 * when it's done" on the loading overlay.
 */
export const useDiagnosticStore = defineStore('diagnostic', () => {
  const session = useSessionStore()

  const sessionId = ref<string | null>(null)
  const messages = ref<ChatEntry[]>([])
  const processing = ref(false)
  const status = ref<string>('')
  const progress = ref<BackendPipelineProgress | null>(null)
  const gaps = ref<UnresolvedKnowledgeGap[]>([])
  const error = ref<string | null>(null)

  let pollTimer: ReturnType<typeof setTimeout> | null = null
  // Whether this store raised the global overlay, so it only ever lowers
  // its own and never one some other action is showing.
  let ownsOverlay = false

  const statusText = computed(() => describeProgress(progress.value))

  function setOverlay(show: boolean) {
    if (show && !session.backgrounded) {
      session.isLoading = true
      session.loadingMessage = statusText.value
      ownsOverlay = true
    } else if (ownsOverlay) {
      session.isLoading = false
      ownsOverlay = false
    }
  }

  async function refreshGaps(id: string) {
    const res = await api.backendClient.getKnowledgeGaps(id)
    const list: UnresolvedKnowledgeGap[] = []
    let idx = 1
    for (const [domain, descriptions] of Object.entries(res.gaps || {})) {
      for (const desc of descriptions || []) {
        list.push({
          id: `gap-${idx++}`,
          title: domain.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
          description: desc,
          status: 'Open'
        })
      }
    }
    gaps.value = list
  }

  function stopPolling() {
    if (pollTimer) clearTimeout(pollTimer)
    pollTimer = null
  }

  async function pollOnce() {
    const id = sessionId.value
    if (!id) return
    try {
      const res = await api.backendClient.getConversation(id)
      if (id !== sessionId.value) return // session switched mid-request
      messages.value = res.messages.map(toChatEntry)
      processing.value = res.processing
      status.value = res.status
      progress.value = res.pipeline_progress ?? null

      if (res.status === 'error') {
        error.value = res.error_message || 'The diagnostic agents hit an unexpected error.'
        processing.value = false
      }
      if (processing.value) {
        setOverlay(true)
        pollTimer = setTimeout(pollOnce, POLL_INTERVAL_MS)
        return
      }
      setOverlay(false)
      await refreshGaps(id).catch((e) => console.warn('Failed to load knowledge gaps:', e))
    } catch (e) {
      // A transient network blip shouldn't end the run: keep polling.
      console.warn('Conversation poll failed, retrying:', e)
      pollTimer = setTimeout(pollOnce, POLL_INTERVAL_MS * 2)
    }
  }

  function startPolling() {
    stopPolling()
    void pollOnce()
  }

  /** Load (or resume) the conversation for the current session, starting the
   *  diagnostic if this session has never run one. Safe to call on every
   *  mount of the Step 3 view. */
  async function load() {
    if (api.USE_MOCKS) {
      messages.value = mockConversation.map(toChatEntry)
      return
    }
    const id = session.sessionId
    if (!id) {
      error.value = 'No active session. Connect a repository first.'
      return
    }
    if (id !== sessionId.value) {
      stopPolling()
      sessionId.value = id
      messages.value = []
      progress.value = null
      gaps.value = []
    } else if (pollTimer) {
      return // already following this session's run
    }
    error.value = null

    try {
      const existing = await api.backendClient.getConversation(id)
      if (existing.messages.length === 0) {
        await api.backendClient.startDiagnostic(id)
      }
      startPolling()
    } catch (e) {
      error.value = `Couldn't start the diagnostic: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  /** Stop the running diagnostic (frees the model for other sessions). */
  async function cancel() {
    const id = sessionId.value
    if (!id || api.USE_MOCKS) return
    stopPolling()
    try {
      await api.backendClient.cancelDiagnostic(id)
    } catch (e) {
      error.value = `Couldn't stop the diagnostic: ${e instanceof Error ? e.message : String(e)}`
    }
    setOverlay(false)
    await pollOnce() // pick up the "stopped" message and status
  }

  /** Start a stopped (or failed) diagnostic again from the beginning. */
  async function restart() {
    const id = sessionId.value
    if (!id || api.USE_MOCKS) return
    error.value = null
    try {
      await api.backendClient.startDiagnostic(id)
      startPolling()
    } catch (e) {
      error.value = `Couldn't restart the diagnostic: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  async function sendMessage(text: string) {
    const id = sessionId.value
    if (!text.trim() || processing.value) return
    if (api.USE_MOCKS || !id) {
      messages.value.push({
        id: `local-${Date.now()}`, sender: 'user', agentInitial: 'You', agentName: 'You', text,
        timestamp: formatTime(new Date().toISOString())
      })
      return
    }
    // Shown right away; replaced by the backend's copy on the next poll.
    messages.value.push({
      id: `pending-${Date.now()}`, sender: 'user', agentInitial: 'You', agentName: 'You', text,
      timestamp: formatTime(new Date().toISOString())
    })
    processing.value = true
    error.value = null
    try {
      await api.backendClient.sendConversationMessage(id, text)
      startPolling()
    } catch (e) {
      processing.value = false
      error.value = `Couldn't send your answer: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  return {
    messages,
    processing,
    status,
    progress,
    statusText,
    gaps,
    error,
    load,
    cancel,
    restart,
    sendMessage,
    stopPolling
  }
})
