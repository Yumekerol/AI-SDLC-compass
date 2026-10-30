import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  RepoSignals,
  UserAnswer,
  DiagnosticReport,
  AppError,
  ConnectPayload
} from '@/types'
import * as api from '@/api'
import { mockRepoSignals } from '@/mocks'

const SESSION_STORAGE_KEY = 'sdlc_compass_session_id'

export const useSessionStore = defineStore('session', () => {
  // Session Identity (Persisted across refreshes in sessionStorage)
  const sessionId = ref<string | null>(sessionStorage.getItem(SESSION_STORAGE_KEY))

  // State
  const repoSignals = ref<RepoSignals | null>(null)
  const answers = ref<Record<string, UserAnswer>>({})
  const diagnostic = ref<DiagnosticReport | null>(null)
  const currentStep = ref<number>(1)

  // Loading & Error states
  const isLoading = ref<boolean>(false)
  const loadingMessage = ref<string>('')
  /** The user chose "notify me when it's done" on the loading overlay: the
   *  running work carries on without the overlay, and a notification (bell +
   *  toast) tells them when it finishes. */
  const backgrounded = ref<boolean>(false)
  const error = ref<AppError | null>(null)
  const lastFailedAction = ref<(() => Promise<void>) | null>(null)

  // Computed properties
  const isConnected = computed(() => !!repoSignals.value)
  const answersList = computed(() => Object.values(answers.value))
  const answeredCount = computed(() => answersList.value.filter((a) => !a.skipped).length)
  const hasDiagnostic = computed(() => !!diagnostic.value)
  /** True when the displayed signals come from the in-memory mock fixture, not a real scan */
  const isMock = computed(() => repoSignals.value?.fromMock !== false)

  // Session ID Synchronization
  function setSessionId(id: string | null) {
    sessionId.value = id
    if (id) {
      sessionStorage.setItem(SESSION_STORAGE_KEY, id)
    } else {
      sessionStorage.removeItem(SESSION_STORAGE_KEY)
    }
  }

  // Error management
  function clearError() {
    error.value = null
  }

  function setError(newError: AppError, retryFn?: () => Promise<void>) {
    error.value = newError
    if (retryFn) {
      lastFailedAction.value = retryFn
    }
  }

  function sendToBackground() {
    backgrounded.value = true
    isLoading.value = false
  }

  async function retryLastAction() {
    if (lastFailedAction.value) {
      clearError()
      await lastFailedAction.value()
    }
  }

  /**
   * Screen 1: Connect repository (URL or ZIP)
   * Calls POST /sessions, uploads ZIP if applicable, calls POST /scan, and polls until complete.
   */
  async function connectRepository(payload: ConnectPayload) {
    backgrounded.value = false
    isLoading.value = true
    loadingMessage.value = 'Connecting and analyzing repository signals...'
    clearError()

    const execute = async () => {
      try {
        isLoading.value = true
        loadingMessage.value = 'Connecting and analyzing repository signals...'

        const signals = await api.scanRepository(payload, (msg) => {
          loadingMessage.value = msg
        }, (id) => setSessionId(id))

        repoSignals.value = signals
        if (signals.sessionId) {
          setSessionId(signals.sessionId)
        }
        currentStep.value = 2
      } catch (err: unknown) {
        const anyErr = err as { code?: string; message?: string }
        if (anyErr.code === 'out_of_scope') {
          setError(
            {
              type: 'out_of_scope',
              title: 'Repository Out of Scope',
              message: 'This PoC supports repositories with ~50 code files in Python, JavaScript, and Java.',
              details: anyErr.message || 'Please choose a smaller repository or upload a focused subset ZIP.',
              canRetry: true,
              retryActionName: 'Try with another repository'
            },
            () => connectRepository(payload)
          )
        } else if (anyErr.code === 'network') {
          setError(
            {
              type: 'network',
              title: 'Connection Failure',
              message: 'Could not connect to the remote repository or backend server. Check your connection or the URL provided.',
              details: anyErr.message,
              canRetry: true,
              retryActionName: 'Retry Scan'
            },
            () => connectRepository(payload)
          )
        } else {
          setError(
            {
              type: 'network',
              title: 'Scan Error',
              message: anyErr.message || 'An unexpected error occurred while scanning the codebase.',
              details: anyErr.message,
              canRetry: true,
              retryActionName: 'Retry Scan'
            },
            () => connectRepository(payload)
          )
        }
      } finally {
        isLoading.value = false
        loadingMessage.value = ''
      }
    }

    await execute()
  }

  /**
   * Screen 2: Update signals from review edits
   * Calls PATCH /sessions/{id}/signals when connected to backend.
   */
  async function updateReviewedSignals(signals: RepoSignals) {
    try {
      isLoading.value = true
      loadingMessage.value = 'Saving signal adjustments...'
      const updated = await api.updateSignals(signals, sessionId.value || undefined)
      repoSignals.value = updated
    } catch (err: unknown) {
      const anyErr = err as { message?: string }
      setError({
        type: 'network',
        title: 'Save Failed',
        message: anyErr.message || 'Unable to update repository signals. Please try again.',
        canRetry: true,
        retryActionName: 'Retry Save'
      })
    } finally {
      isLoading.value = false
      loadingMessage.value = ''
    }
  }

  /**
   * Screen 2 -> 3: Confirm reviewed signals
   * Calls POST /sessions/{id}/confirm-signals when connected to backend.
   */
  async function confirmSignals() {
    backgrounded.value = false
    try {
      isLoading.value = true
      loadingMessage.value = 'Confirming repository signals...'
      await api.confirmSignals(sessionId.value || undefined)
      currentStep.value = 3
    } catch (err: unknown) {
      const anyErr = err as { message?: string }
      setError({
        type: 'network',
        title: 'Confirmation Failed',
        message: anyErr.message || 'Could not lock signals for diagnostic. Please try again.',
        canRetry: true,
        retryActionName: 'Retry Confirmation'
      })
      throw err
    } finally {
      isLoading.value = false
      loadingMessage.value = ''
    }
  }

  /**
   * Screen 3: Record an answer to a question (preserves all answers)
   */
  async function recordAnswer(answer: UserAnswer) {
    answers.value[answer.questionId] = answer
    try {
      await api.submitAnswer(answer)
    } catch {
      // Offline fallback: keep local answer stored in session state
      console.warn('API sync warning: answer cached locally in Pinia session')
    }
  }

  /**
   * Skip a question
   */
  async function skipQuestion(questionId: string, topic: string) {
    const skippedAnswer: UserAnswer = {
      questionId,
      topic,
      answerText: 'Skipped by user',
      skipped: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    await recordAnswer(skippedAnswer)
  }

  /**
   * Screen 4: Generate diagnostic from signals + answers
   */
  async function generateDiagnosticReport() {
    isLoading.value = true
    loadingMessage.value = 'Synthesizing evidence & generating 4-domain AI diagnostic...'
    clearError()

    const execute = async () => {
      try {
        isLoading.value = true
        loadingMessage.value = 'Synthesizing evidence & generating 4-domain AI diagnostic...'
        const signals = repoSignals.value || mockRepoSignals
        const report = await api.generateDiagnostic(
          signals,
          answersList.value,
          sessionId.value || undefined,
          (msg) => {
            loadingMessage.value = msg
          }
        )
        diagnostic.value = report
        currentStep.value = 4
      } catch (err: unknown) {
        const anyErr = err as { code?: string; message?: string }
        if (anyErr.code === 'ai_down' || anyErr.code === 'timeout') {
          setError(
            {
              type: 'ai_down',
              title: anyErr.code === 'timeout' ? 'Synthesis Timed Out' : 'AI Service Unavailable',
              message:
                anyErr.code === 'timeout'
                  ? 'Report generation timed out. Your answers and reviewed signals are safely preserved.'
                  : 'The AI Diagnostic engine is currently unreachable. Your answers are safely preserved.',
              details: 'Click retry to re-submit synthesis without losing any input.',
              canRetry: true,
              retryActionName: 'Retry AI Generation'
            },
            () => generateDiagnosticReport()
          )
        } else {
          setError(
            {
              type: 'network',
              title: 'Generation Failed',
              message: anyErr.message || 'Unable to generate the diagnostic report. Your answers are preserved.',
              canRetry: true,
              retryActionName: 'Retry Generation'
            },
            () => generateDiagnosticReport()
          )
        }
      } finally {
        isLoading.value = false
        loadingMessage.value = ''
      }
    }

    await execute()
  }

  /**
   * Regenerate report (e.g. from Report screen)
   */
  async function regenerateReport() {
    isLoading.value = true
    loadingMessage.value = 'Regenerating diagnostic report with fresh recommendations...'
    clearError()

    const execute = async () => {
      try {
        isLoading.value = true
        loadingMessage.value = 'Regenerating diagnostic report with fresh recommendations...'
        const signals = repoSignals.value || mockRepoSignals
        const report = await api.regenerateDiagnostic(
          signals,
          answersList.value,
          sessionId.value || undefined,
          (msg) => {
            loadingMessage.value = msg
          }
        )
        diagnostic.value = report
      } catch (err: unknown) {
        const anyErr = err as { message?: string }
        setError(
          {
            type: 'ai_down',
            title: 'Regeneration Error',
            message: anyErr.message || 'Could not regenerate report at this time. Existing report preserved.',
            canRetry: true,
            retryActionName: 'Retry Regeneration'
          },
          () => regenerateReport()
        )
      } finally {
        isLoading.value = false
        loadingMessage.value = ''
      }
    }

    await execute()
  }

  function setStep(step: number) {
    currentStep.value = step
  }

  // Reload signals from the backend session after a page refresh. Sample
  // signals are used only in mock mode — in real mode a failure is shown as
  // an error, never papered over with sample data.
  async function ensureSampleSignals() {
    if (repoSignals.value) return
    if (api.USE_MOCKS) {
      repoSignals.value = JSON.parse(JSON.stringify(mockRepoSignals))
      return
    }
    if (!sessionId.value) {
      setError({
        type: 'network',
        title: 'No active session',
        message: 'Connect a repository first. There is no scan to show yet.',
        canRetry: false
      })
      return
    }
    try {
      repoSignals.value = await api.getSignals(sessionId.value)
    } catch (err: unknown) {
      const anyErr = err as { message?: string }
      setError(
        {
          type: 'network',
          title: "Couldn't load signals from the scanner",
          message: anyErr.message || 'The backend did not return this session\'s scan results.',
          canRetry: true,
          retryActionName: 'Retry'
        },
        () => ensureSampleSignals()
      )
    }
  }

  return {
    // State
    sessionId,
    repoSignals,
    answers,
    diagnostic,
    currentStep,
    isLoading,
    loadingMessage,
    backgrounded,
    error,
    // Computed
    isConnected,
    answersList,
    answeredCount,
    hasDiagnostic,
    isMock,
    // Actions
    setSessionId,
    sendToBackground,
    connectRepository,
    updateReviewedSignals,
    confirmSignals,
    recordAnswer,
    skipQuestion,
    generateDiagnosticReport,
    regenerateReport,
    clearError,
    retryLastAction,
    setStep,
    ensureSampleSignals
  }
})
