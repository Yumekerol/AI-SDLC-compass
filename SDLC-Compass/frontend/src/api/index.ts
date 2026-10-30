import type {
  RepoSignals,
  Question,
  UserAnswer,
  DiagnosticReport,
  AdvisorContext,
  AdvisorMessage,
  ConnectPayload,
  AppNotification
} from '@/types'
import {
  mockRepoSignals,
  mockQuestions,
  mockDiagnosticReport,
  mockAdvisorContext,
  mockInitialAdvisorMessages,
  mockNotifications
} from '@/mocks'
import * as backendClient from './backendClient'
import {
  adaptBackendSignalsToRepoSignals,
  adaptRepoSignalsToPatchRequest,
  adaptBackendReportToDiagnosticReport
} from './adapters'

export * from './types'
export * from './adapters'
export * as backendClient from './backendClient'

/**
 * Mock toggle and backend base URL configuration.
 * Defaults to mocks (true) unless explicitly set to 'false' in VITE_USE_MOCKS.
 */
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false'
export const API_BASE = backendClient.API_BASE

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// Local in-memory mock state during session
let currentSignals: RepoSignals = JSON.parse(JSON.stringify(mockRepoSignals))
let currentAnswers: UserAnswer[] = []
let currentDiagnostic: DiagnosticReport = JSON.parse(JSON.stringify(mockDiagnosticReport))
let currentAdvisorMessages: AdvisorMessage[] = JSON.parse(JSON.stringify(mockInitialAdvisorMessages))
let currentNotifications: AppNotification[] = JSON.parse(JSON.stringify(mockNotifications))

/**
 * Scan a repository (Git URL or ZIP file upload)
 * Connects to FastAPI backend if USE_MOCKS is false.
 */
export async function scanRepository(
  payload: ConnectPayload,
  onProgress?: (message: string) => void,
  // Called as soon as the backend session exists — before the (possibly
  // long) scan — so notifications for it can be followed while it runs.
  onSessionCreated?: (sessionId: string) => void
): Promise<RepoSignals> {
  if (!USE_MOCKS) {
    onProgress?.('Creating diagnostic session on backend...')
    const sessionRes = await backendClient.createSession(payload)
    const sessionId = sessionRes.session_id
    onSessionCreated?.(sessionId)

    if (payload.source === 'zip' && payload.file) {
      onProgress?.('Uploading ZIP repository archive...')
      await backendClient.uploadZipArchive(sessionId, payload.file)
    }

    onProgress?.('Starting Light Scanner...')
    await backendClient.triggerScan(sessionId)

    onProgress?.('Analyzing code structure and dependencies...')
    await backendClient.pollSessionStatus(sessionId, onProgress)

    onProgress?.('Retrieving extracted signals...')
    const rawSignals = await backendClient.getSignals(sessionId)
    currentSignals = adaptBackendSignalsToRepoSignals(rawSignals)
    return currentSignals
  }

  // --- Mock Mode ---
  await delay(1200)

  // Simulation: out of scope if URL contains 'out-of-scope' or 'invalid'
  if (payload.gitUrl && payload.gitUrl.toLowerCase().includes('out-of-scope')) {
    const error = new Error('Repository is out of PoC scope: exceeds 50 files or unsupported language.')
    ;(error as unknown as { code: string }).code = 'out_of_scope'
    throw error
  }

  // Simulation: network error if URL contains 'network-error'
  if (payload.gitUrl && payload.gitUrl.toLowerCase().includes('network-error')) {
    const error = new Error('Network error: Unable to reach Git host or server.')
    ;(error as unknown as { code: string }).code = 'network'
    throw error
  }

  // Clone sample data and adapt repo name
  const signals: RepoSignals = JSON.parse(JSON.stringify(mockRepoSignals))
  if (payload.gitUrl) {
    signals.repoUrl = payload.gitUrl
    const parts = payload.gitUrl.split('/')
    const last = parts[parts.length - 1]?.replace('.git', '')
    if (last) {
      signals.repoName = last.charAt(0).toUpperCase() + last.slice(1)
    }
  } else if (payload.file) {
    signals.repoName = payload.file.name.replace(/\.[^/.]+$/, '')
    signals.repoUrl = undefined
  }
  currentSignals = signals
  return currentSignals
}

/**
 * Get current repository signals
 */
export async function getSignals(sessionId?: string): Promise<RepoSignals> {
  if (!USE_MOCKS && !sessionId) {
    throw new Error('No active session — connect a repository first.')
  }
  if (!USE_MOCKS && sessionId) {
    const rawSignals = await backendClient.getSignals(sessionId)
    currentSignals = adaptBackendSignalsToRepoSignals(rawSignals)
    return currentSignals
  }
  await delay(400)
  return currentSignals
}

/**
 * Update modified repository signals
 */
export async function updateSignals(updated: RepoSignals, sessionId?: string): Promise<RepoSignals> {
  if (!USE_MOCKS && !(sessionId || updated.sessionId)) {
    throw new Error('No active session — connect a repository first.')
  }
  if (!USE_MOCKS && (sessionId || updated.sessionId)) {
    const targetSessionId = sessionId || updated.sessionId!
    const patchPayload = adaptRepoSignalsToPatchRequest(updated)
    await backendClient.patchSignals(targetSessionId, patchPayload)
    const refreshed = await backendClient.getSignals(targetSessionId)
    currentSignals = adaptBackendSignalsToRepoSignals(refreshed)
    return currentSignals
  }

  await delay(500)
  currentSignals = JSON.parse(JSON.stringify(updated))
  return currentSignals
}

/**
 * Confirm reviewed signals and lock them before moving to diagnostic Q&A
 */
export async function confirmSignals(sessionId?: string): Promise<{ success: boolean; status?: string }> {
  if (!USE_MOCKS && !sessionId) {
    // Real-backend mode with no session has nothing to confirm server-side —
    // a real error, not a silent mock success that advances the user past a
    // step nothing actually happened for.
    throw new Error('No active session — the repository connection may have been lost. Please reconnect.')
  }
  if (!USE_MOCKS && sessionId) {
    const res = await backendClient.confirmSignals(sessionId)
    return { success: true, status: res.status }
  }
  await delay(300)
  return { success: true }
}

/**
 * Get context clarification questions
 */
export async function getQuestions(): Promise<Question[]> {
  await delay(400)
  return mockQuestions
}

/**
 * Submit user answer to a question
 */
export async function submitAnswer(answer: UserAnswer): Promise<{ success: boolean; nextIndex: number }> {
  await delay(350)
  const existingIdx = currentAnswers.findIndex((a) => a.questionId === answer.questionId)
  if (existingIdx >= 0) {
    currentAnswers[existingIdx] = answer
  } else {
    currentAnswers.push(answer)
  }
  return { success: true, nextIndex: currentAnswers.length }
}

/**
 * Generate diagnostic report.
 * When USE_MOCKS is false, calls continue-diagnostic, gets report JSON, and adapts to 4 domain cards.
 */
export async function generateDiagnostic(
  signals: RepoSignals,
  answers: UserAnswer[],
  sessionId?: string,
  onProgress?: (message: string) => void
): Promise<DiagnosticReport> {
  if (!USE_MOCKS && !(sessionId || signals.sessionId)) {
    // Never fall through to the sample report in real mode.
    throw new Error('No active session — connect a repository first.')
  }
  if (!USE_MOCKS && (sessionId || signals.sessionId)) {
    const targetSessionId = sessionId || signals.sessionId!
    onProgress?.('Synthesizing evidence across all 4 specialist domains...')
    await backendClient.continueDiagnostic(targetSessionId)

    onProgress?.('Retrieving synthesized diagnostic assessment...')
    const rawReport = await backendClient.getReport(targetSessionId)
    currentDiagnostic = adaptBackendReportToDiagnosticReport(rawReport)
    return currentDiagnostic
  }

  // --- Mock Mode ---
  await delay(1500)

  // Simulation check for AI downtime trigger
  const hasAiDownTrigger = answers.some((a) => a.answerText.toLowerCase().includes('trigger-ai-error'))
  if (hasAiDownTrigger) {
    const error = new Error('AI Diagnostic engine service is temporarily unavailable. Please retry.')
    ;(error as unknown as { code: string }).code = 'ai_down'
    throw error
  }

  currentDiagnostic = JSON.parse(JSON.stringify(mockDiagnosticReport))
  currentDiagnostic.repoName = signals.repoName
  return currentDiagnostic
}

/**
 * Fetch an already-generated report without re-running synthesis — for
 * loading ReportView directly (a page reload, or navigating back to it)
 * when the report was generated earlier in the session and just needs to
 * be read, not regenerated. Throws if the backend has no report yet for
 * this session (diagnostic not finished) — callers should show a "not
 * ready" state rather than fabricating one.
 */
export async function getExistingDiagnostic(sessionId: string): Promise<DiagnosticReport> {
  const rawReport = await backendClient.getReport(sessionId)
  currentDiagnostic = adaptBackendReportToDiagnosticReport(rawReport)
  return currentDiagnostic
}

/**
 * Regenerate diagnostic report (creating a fresh version)
 */
export async function regenerateDiagnostic(
  signals: RepoSignals,
  answers: UserAnswer[],
  sessionId?: string,
  onProgress?: (message: string) => void
): Promise<DiagnosticReport> {
  return generateDiagnostic(signals, answers, sessionId, onProgress)
}

/**
 * Get Advisor context
 */
export async function getAdvisorContext(): Promise<AdvisorContext> {
  await delay(300)
  return mockAdvisorContext
}

/**
 * Get Advisor chat messages
 */
export async function getAdvisorMessages(): Promise<AdvisorMessage[]> {
  await delay(300)
  return currentAdvisorMessages
}

/**
 * Send message to Advisor chat
 * Kept in its own function so it can easily swap to a real endpoint later without touching the view.
 */
export async function sendAdvisorMessage(content: string): Promise<AdvisorMessage> {
  await delay(800)

  const userMsg: AdvisorMessage = {
    id: `msg-${Date.now()}`,
    sender: 'user',
    senderName: 'Team representative',
    content,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  currentAdvisorMessages.push(userMsg)

  // Automated advisor response
  const responseMsg: AdvisorMessage = {
    id: `msg-${Date.now() + 1}`,
    sender: 'advisor',
    senderName: 'Advisor Specialist',
    role: 'Synthesizer',
    content: `Understood: "${content}". Based on your 48-file scope and Scrum setup, this refinement aligns with keeping early AI practices bounded and verifiable. We've updated your session context accordingly.`,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  currentAdvisorMessages.push(responseMsg)

  return responseMsg
}

/**
 * Export diagnostic report to PDF (or HTML deliverable if PDF renderer not installed)
 * Downloads as a binary blob.
 */
export async function exportPdfReport(
  sessionId?: string
): Promise<{ success: boolean; filename: string; isPdf?: boolean }> {
  if (!USE_MOCKS && !sessionId) {
    // Real-backend mode with no session is a real error, not something to
    // fake a successful download for.
    throw new Error('No active session — connect a repository before exporting a report.')
  }

  if (!USE_MOCKS && sessionId) {
    const { blob, filename, isPdf } = await backendClient.downloadReportBlob(sessionId)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    return {
      success: true,
      filename,
      isPdf
    }
  }

  // --- Mock Mode ---
  await delay(800)
  return {
    success: true,
    filename: `AI-SDLC-Compass-Report-${Date.now()}.pdf`,
    isPdf: true
  }
}


/**
 * Fetch notifications for current session
 */
export async function fetchNotifications(
  sessionId?: string,
  unreadOnly = false
): Promise<AppNotification[]> {
  if (!USE_MOCKS) {
    // No session yet means no notifications yet — never sample ones.
    if (!sessionId) return []
    const res = await backendClient.getNotifications(sessionId, unreadOnly)
    return res.notifications
  }
  await delay(150)
  if (unreadOnly) {
    return currentNotifications.filter((n) => !n.read)
  }
  return [...currentNotifications]
}

/**
 * Mark a single notification as read
 */
export async function markNotificationAsRead(
  notificationId: string,
  sessionId?: string
): Promise<void> {
  if (!USE_MOCKS) {
    if (sessionId) await backendClient.markNotificationRead(sessionId, notificationId)
    return
  }
  await delay(100)
  const item = currentNotifications.find((n) => n.id === notificationId)
  if (item) {
    item.read = true
  }
}

/**
 * Mark all notifications as read
 */
export async function markAllNotificationsAsRead(
  sessionId?: string
): Promise<void> {
  if (!USE_MOCKS) {
    if (sessionId) await backendClient.markAllNotificationsRead(sessionId)
    return
  }
  await delay(100)
  currentNotifications.forEach((n) => {
    n.read = true
  })
}

/**
 * Clear all notifications
 */
export async function clearAllNotifications(
  sessionId?: string
): Promise<void> {
  if (!USE_MOCKS) {
    if (sessionId) await backendClient.clearAllNotifications(sessionId)
    return
  }
  await delay(100)
  currentNotifications = []
}

/**
 * Delete a single notification
 */
export async function deleteNotification(
  notificationId: string,
  sessionId?: string
): Promise<void> {
  if (!USE_MOCKS) {
    if (sessionId) await backendClient.deleteNotification(sessionId, notificationId)
    return
  }
  await delay(100)
  currentNotifications = currentNotifications.filter((n) => n.id !== notificationId)
}

