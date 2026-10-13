import type {
  RepoSignals,
  Question,
  UserAnswer,
  DiagnosticReport,
  AdvisorContext,
  AdvisorMessage,
  ConnectPayload
} from '@/types'
import {
  mockRepoSignals,
  mockQuestions,
  mockDiagnosticReport,
  mockAdvisorContext,
  mockInitialAdvisorMessages
} from '@/mocks'

/**
 * Mock toggle and backend base URL configuration.
 * Defaults to mocks (true) unless explicitly set to 'false' in VITE_USE_MOCKS.
 */
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false'
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// Local in-memory mock state during session
let currentSignals: RepoSignals = JSON.parse(JSON.stringify(mockRepoSignals))
let currentAnswers: UserAnswer[] = []
let currentDiagnostic: DiagnosticReport = JSON.parse(JSON.stringify(mockDiagnosticReport))
let currentAdvisorMessages: AdvisorMessage[] = JSON.parse(JSON.stringify(mockInitialAdvisorMessages))

/**
 * Scan a repository (Git URL or ZIP file upload)
 */
export async function scanRepository(payload: ConnectPayload): Promise<RepoSignals> {
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
export async function getSignals(): Promise<RepoSignals> {
  await delay(400)
  return currentSignals
}

/**
 * Update modified repository signals
 */
export async function updateSignals(updated: RepoSignals): Promise<RepoSignals> {
  await delay(500)
  currentSignals = JSON.parse(JSON.stringify(updated))
  return currentSignals
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
 * Generate diagnostic report for the 6 SDLC phases
 */
export async function generateDiagnostic(
  signals: RepoSignals,
  answers: UserAnswer[]
): Promise<DiagnosticReport> {
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
 * Regenerate diagnostic report (creating a fresh version)
 */
export async function regenerateDiagnostic(
  _signals: RepoSignals,
  _answers: UserAnswer[]
): Promise<DiagnosticReport> {
  await delay(1400)
  const updated = JSON.parse(JSON.stringify(mockDiagnosticReport))
  updated.generatedAt = 'Regenerated just now'
  currentDiagnostic = updated
  return currentDiagnostic
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
 * Export diagnostic report to PDF
 */
export async function exportPdfReport(): Promise<{ success: boolean; filename: string }> {
  await delay(800)
  return {
    success: true,
    filename: `AI-SDLC-Compass-Report-${Date.now()}.pdf`
  }
}
