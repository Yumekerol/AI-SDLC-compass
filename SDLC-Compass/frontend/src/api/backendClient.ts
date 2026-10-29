import type { ConnectPayload } from '@/types/common'
import type { AppNotification } from '@/types/notifications'
import type {
  BackendCreateSessionResponse,
  BackendSessionStatusResponse,
  BackendUploadZipResponse,
  BackendScanTriggerResponse,
  BackendSignalsResponse,
  BackendPatchSignalsRequest,
  BackendDiagnoseResponse,
  BackendConversationResponse,
  BackendSendMessageResponse,
  BackendKnowledgeGapsResponse,
  BackendAdvisorMessagesResponse,
  BackendContinueDiagnosticResponse,
  BackendSynthesisOutput
} from './types'

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'

/**
 * Max wait, in ms, for any long-running Agent Service turn — report
 * synthesis, but also a /diagnose or /conversation call whose background
 * task may run several specialists back to back before the next pause.
 * Configurable via VITE_REPORT_TIMEOUT_MS (default 180 s).
 */
export const REPORT_TIMEOUT_MS = Number(import.meta.env.VITE_REPORT_TIMEOUT_MS) || 180_000

class ApiError extends Error {
  code: string
  status?: number

  constructor(message: string, code = 'unknown', status?: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  let response: Response

  try {
    response = await fetch(url, {
      ...options,
      headers: {
        ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...options.headers
      }
    })
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Network request failed'
    throw new ApiError(`Unable to reach backend server at ${API_BASE}. (${errorMsg})`, 'network')
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const errJson = await response.json()
      if (errJson && errJson.detail) {
        detail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail)
      }
    } catch {
      // Body not JSON
    }

    const detailLower = detail.toLowerCase()
    let code = 'api_error'
    if (
      detailLower.includes('out of scope') ||
      detailLower.includes('unsupported') ||
      detailLower.includes('exceeds')
    ) {
      code = 'out_of_scope'
    } else if (response.status >= 500) {
      code = 'server_error'
    }

    throw new ApiError(detail, code, response.status)
  }

  return response.json() as Promise<T>
}

/**
 * Step 1: Create a new diagnostic session
 */
export async function createSession(payload: ConnectPayload): Promise<BackendCreateSessionResponse> {
  return request<BackendCreateSessionResponse>('/sessions', {
    method: 'POST',
    body: JSON.stringify({
      source_type: payload.source,
      git_url: payload.gitUrl || null,
      consent_given: true
    })
  })
}

/**
 * Step 1: Upload a ZIP repository archive
 */
export async function uploadZipArchive(sessionId: string, file: File): Promise<BackendUploadZipResponse> {
  const formData = new FormData()
  formData.append('archive', file)

  return request<BackendUploadZipResponse>(`/sessions/${sessionId}/upload`, {
    method: 'POST',
    body: formData
  })
}

/**
 * Step 1 -> 2: Trigger deterministic Light Scanner execution
 */
export async function triggerScan(sessionId: string): Promise<BackendScanTriggerResponse> {
  return request<BackendScanTriggerResponse>(`/sessions/${sessionId}/scan`, {
    method: 'POST'
  })
}

/**
 * Poll session status until scan finishes or errors
 */
export async function pollSessionStatus(
  sessionId: string,
  onProgress?: (message: string) => void,
  maxWaitMs = 60000
): Promise<BackendSessionStatusResponse> {
  const startTime = Date.now()

  while (Date.now() - startTime < maxWaitMs) {
    await new Promise((resolve) => setTimeout(resolve, 800))

    const session = await request<BackendSessionStatusResponse>(`/sessions/${sessionId}`, {
      method: 'GET'
    })

    if (session.status === 'ingesting') {
      onProgress?.('Cloning repository archive from Git...')
    } else if (session.status === 'scanning') {
      onProgress?.('Running deterministic Light Scanner across source files...')
    } else if (
      session.status === 'awaiting_signal_review' ||
      session.status === 'awaiting_team_context' ||
      session.status === 'complete'
    ) {
      return session
    } else if (session.status === 'error') {
      const msg = session.error_message || 'Scanner encountered an unexpected error.'
      const lower = msg.toLowerCase()
      const code =
        lower.includes('out of scope') || lower.includes('exceeds') || lower.includes('supported')
          ? 'out_of_scope'
          : 'network'
      throw new ApiError(msg, code)
    }
  }

  throw new ApiError('Repository scan timed out after 60 seconds.', 'network')
}

/**
 * Step 2: Fetch reviewed signals
 */
export async function getSignals(sessionId: string): Promise<BackendSignalsResponse> {
  return request<BackendSignalsResponse>(`/sessions/${sessionId}/signals`, {
    method: 'GET'
  })
}

/**
 * Step 2: Patch updated signals overrides
 */
export async function patchSignals(
  sessionId: string,
  patchData: BackendPatchSignalsRequest
): Promise<unknown> {
  return request(`/sessions/${sessionId}/signals`, {
    method: 'PATCH',
    body: JSON.stringify(patchData)
  })
}

/**
 * Step 2 -> 3: Confirm signals and proceed to diagnostic questions
 */
export async function confirmSignals(sessionId: string): Promise<{ session_id: string; status: string }> {
  return request<{ session_id: string; status: string }>(`/sessions/${sessionId}/confirm-signals`, {
    method: 'POST'
  })
}

/**
 * Step 3: Start diagnostic Q&A and fetch kickoff agent messages
 */
export async function startDiagnostic(sessionId: string): Promise<BackendDiagnoseResponse> {
  return request<BackendDiagnoseResponse>(`/sessions/${sessionId}/diagnose`, {
    method: 'POST'
  })
}

/**
 * Step 3: Get full diagnostic conversation history and agent statuses
 */
export async function getConversation(sessionId: string): Promise<BackendConversationResponse> {
  return request<BackendConversationResponse>(`/sessions/${sessionId}/conversation`, {
    method: 'GET'
  })
}

/**
 * Step 3: Poll the conversation until the backend's current turn finishes.
 * /diagnose and /conversation both return immediately and run the actual
 * specialist pipeline call in the background (it can take as long as a full
 * specialist run, or several back to back) — this is how the frontend finds
 * out when that's done and what was said, the same pattern pollSessionStatus
 * already uses for the Step 1→2 scan.
 */
export async function pollConversation(
  sessionId: string,
  onProgress?: (message: string) => void,
  maxWaitMs = REPORT_TIMEOUT_MS
): Promise<BackendConversationResponse> {
  const startTime = Date.now()

  while (Date.now() - startTime < maxWaitMs) {
    const res = await getConversation(sessionId)

    if (res.status === 'error') {
      throw new ApiError(
        res.error_message || 'The diagnostic agents encountered an unexpected error.',
        'server_error'
      )
    }
    if (!res.processing) {
      return res
    }

    onProgress?.('Specialists are reviewing the repository and may ask a clarifying question...')
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }

  throw new ApiError('Diagnostic conversation timed out waiting for a response.', 'timeout')
}

/**
 * Step 3: Send user response in diagnostic conversation
 */
export async function sendConversationMessage(
  sessionId: string,
  content: string,
  respondingToQuestions?: string[]
): Promise<BackendSendMessageResponse> {
  return request<BackendSendMessageResponse>(`/sessions/${sessionId}/conversation`, {
    method: 'POST',
    body: JSON.stringify({
      content,
      responding_to_questions: respondingToQuestions || []
    })
  })
}

/**
 * Step 3: Fetch unresolved knowledge gaps for side panel
 */
export async function getKnowledgeGaps(sessionId: string): Promise<BackendKnowledgeGapsResponse> {
  return request<BackendKnowledgeGapsResponse>(`/sessions/${sessionId}/knowledge-gaps`, {
    method: 'GET'
  })
}

/**
 * Step 5: Fetch advisor/support chat history (persists across reloads,
 * unlike the Agent Service's own in-memory conversation state)
 */
export async function getAdvisorMessages(sessionId: string): Promise<BackendAdvisorMessagesResponse> {
  return request<BackendAdvisorMessagesResponse>(`/sessions/${sessionId}/advisor/messages`, {
    method: 'GET'
  })
}

/**
 * Step 5: Send a message to the advisor and get its reply. A single bounded
 * call, not pipeline-backgrounded — no polling needed here.
 */
export async function sendAdvisorMessage(
  sessionId: string,
  content: string
): Promise<BackendAdvisorMessagesResponse> {
  return request<BackendAdvisorMessagesResponse>(`/sessions/${sessionId}/advisor/messages`, {
    method: 'POST',
    body: JSON.stringify({ content })
  })
}

/**
 * Step 3: Save draft of current conversation state
 */
export async function saveDraft(
  sessionId: string,
  conversation?: unknown[],
  agentStatuses?: Record<string, unknown>
): Promise<{ status: string }> {
  return request<{ status: string }>(`/sessions/${sessionId}/draft`, {
    method: 'POST',
    body: JSON.stringify({
      conversation,
      agent_statuses: agentStatuses
    })
  })
}

/**
 * Step 3 -> 4: Trigger report synthesis with timeout and retry support
 */
export async function continueDiagnostic(
  sessionId: string,
  timeoutMs = REPORT_TIMEOUT_MS
): Promise<BackendContinueDiagnosticResponse> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  const timeoutSecs = Math.round(timeoutMs / 1000)

  try {
    const res = await request<BackendContinueDiagnosticResponse>(
      `/sessions/${sessionId}/continue-diagnostic`,
      {
        method: 'POST',
        signal: controller.signal
      }
    )
    clearTimeout(timeoutId)
    return res
  } catch (err: unknown) {
    clearTimeout(timeoutId)
    if (err instanceof Error && err.name === 'AbortError') {
      throw new ApiError(
        `Diagnostic synthesis timed out after ${timeoutSecs} seconds. The agents may still be processing.`,
        'timeout'
      )
    }
    throw err
  }
}

/**
 * Step 4: Fetch final synthesized diagnostic report JSON
 */
export async function getReport(sessionId: string): Promise<BackendSynthesisOutput> {
  return request<BackendSynthesisOutput>(`/sessions/${sessionId}/report`, {
    method: 'GET'
  })
}

/**
 * Step 4: Download PDF report as a binary blob
 */
export async function downloadReportBlob(
  sessionId: string
): Promise<{ blob: Blob; filename: string; isPdf: boolean }> {
  const url = `${API_BASE}/sessions/${sessionId}/report/pdf`
  let response: Response

  try {
    response = await fetch(url)
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Network request failed'
    throw new ApiError(`Unable to download report from ${url}. (${errorMsg})`, 'network')
  }

  if (!response.ok) {
    throw new ApiError(`Failed to download report (HTTP ${response.status})`, 'api_error', response.status)
  }

  const contentType = response.headers.get('content-type') || ''
  const isPdf = contentType.includes('pdf')
  const disposition = response.headers.get('content-disposition') || ''
  let filename = isPdf
    ? `AI-SDLC-Compass-Report-${sessionId.slice(0, 8)}.pdf`
    : `AI-SDLC-Compass-Report-${sessionId.slice(0, 8)}.html`

  const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
  if (match && match[1]) {
    filename = match[1].replace(/['"]/g, '')
  }

  const blob = await response.blob()
  return { blob, filename, isPdf }
}


/**
 * Notifications: Fetch session notifications
 */
export async function getNotifications(
  sessionId: string,
  unreadOnly = false
): Promise<{ session_id: string; notifications: AppNotification[] }> {
  const query = unreadOnly ? '?unread_only=true' : ''
  return request<{ session_id: string; notifications: AppNotification[] }>(
    `/sessions/${sessionId}/notifications${query}`,
    { method: 'GET' }
  )
}

/**
 * Notifications: Mark a single notification as read
 */
export async function markNotificationRead(
  sessionId: string,
  notificationId: string
): Promise<{ session_id: string; notification: AppNotification }> {
  return request<{ session_id: string; notification: AppNotification }>(
    `/sessions/${sessionId}/notifications/${notificationId}/read`,
    { method: 'POST' }
  )
}

/**
 * Notifications: Mark all notifications as read
 */
export async function markAllNotificationsRead(
  sessionId: string
): Promise<{ session_id: string; notifications: AppNotification[] }> {
  return request<{ session_id: string; notifications: AppNotification[] }>(
    `/sessions/${sessionId}/notifications/read-all`,
    { method: 'POST' }
  )
}

/**
 * Notifications: Clear all notifications for session
 */
export async function clearAllNotifications(
  sessionId: string
): Promise<{ session_id: string; notifications: [] }> {
  return request<{ session_id: string; notifications: [] }>(
    `/sessions/${sessionId}/notifications`,
    { method: 'DELETE' }
  )
}

/**
 * Notifications: Delete single notification
 */
export async function deleteNotification(
  sessionId: string,
  notificationId: string
): Promise<{ session_id: string; notification_id: string; deleted: boolean }> {
  return request<{ session_id: string; notification_id: string; deleted: boolean }>(
    `/sessions/${sessionId}/notifications/${notificationId}`,
    { method: 'DELETE' }
  )
}

