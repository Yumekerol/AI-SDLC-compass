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

export const useSessionStore = defineStore('session', () => {
  // State
  const repoSignals = ref<RepoSignals | null>(null)
  const answers = ref<Record<string, UserAnswer>>({})
  const diagnostic = ref<DiagnosticReport | null>(null)
  const currentStep = ref<number>(1)

  // Loading & Error states
  const isLoading = ref<boolean>(false)
  const loadingMessage = ref<string>('')
  const error = ref<AppError | null>(null)
  const lastFailedAction = ref<(() => Promise<void>) | null>(null)

  // Computed properties
  const isConnected = computed(() => !!repoSignals.value)
  const answersList = computed(() => Object.values(answers.value))
  const answeredCount = computed(() => answersList.value.filter((a) => !a.skipped).length)
  const hasDiagnostic = computed(() => !!diagnostic.value)

  // Actions
  function clearError() {
    error.value = null
  }

  function setError(newError: AppError, retryFn?: () => Promise<void>) {
    error.value = newError
    if (retryFn) {
      lastFailedAction.value = retryFn
    }
  }

  async function retryLastAction() {
    if (lastFailedAction.value) {
      clearError()
      await lastFailedAction.value()
    }
  }

  /**
   * Screen 1: Connect repository (URL or ZIP)
   */
  async function connectRepository(payload: ConnectPayload) {
    isLoading.value = true
    loadingMessage.value = 'Connecting and analyzing repository signals...'
    clearError()

    const execute = async () => {
      try {
        isLoading.value = true
        loadingMessage.value = 'Connecting and analyzing repository signals...'
        const signals = await api.scanRepository(payload)
        repoSignals.value = signals
        currentStep.value = 2
      } catch (err: unknown) {
        const anyErr = err as { code?: string; message?: string }
        if (anyErr.code === 'out_of_scope') {
          setError(
            {
              type: 'out_of_scope',
              title: 'Repository Out of Scope',
              message: 'This PoC supports repositories with ~50 code files in Python, JavaScript, and Java.',
              details: 'Please choose a smaller repository or upload a focused subset ZIP.',
              canRetry: true,
              retryActionName: 'Try with another repository'
            },
            () => connectRepository(payload)
          )
        } else if (anyErr.code === 'network') {
          setError(
            {
              type: 'network',
              title: 'Network Connection Failure',
              message: 'Could not connect to the remote repository. Check your connection or the URL provided.',
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
   */
  async function updateReviewedSignals(signals: RepoSignals) {
    try {
      isLoading.value = true
      loadingMessage.value = 'Saving signal adjustments...'
      const updated = await api.updateSignals(signals)
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
    loadingMessage.value = 'Synthesizing evidence & generating 6-phase AI diagnostic...'
    clearError()

    const execute = async () => {
      try {
        isLoading.value = true
        loadingMessage.value = 'Synthesizing evidence & generating 6-phase AI diagnostic...'
        const signals = repoSignals.value || mockRepoSignals
        const report = await api.generateDiagnostic(signals, answersList.value)
        diagnostic.value = report
        currentStep.value = 4
      } catch (err: unknown) {
        const anyErr = err as { code?: string; message?: string }
        if (anyErr.code === 'ai_down') {
          setError(
            {
              type: 'ai_down',
              title: 'AI Service Unavailable',
              message: 'The AI Diagnostic engine is currently unreachable. Your answers are safely preserved.',
              details: 'Click retry to re-submit your signals and answers without losing any input.',
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
        const report = await api.regenerateDiagnostic(signals, answersList.value)
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

  // Pre-seed sample signals if user visits /signals directly for inspection/testing
  function ensureSampleSignals() {
    if (!repoSignals.value) {
      repoSignals.value = JSON.parse(JSON.stringify(mockRepoSignals))
    }
  }

  return {
    // State
    repoSignals,
    answers,
    diagnostic,
    currentStep,
    isLoading,
    loadingMessage,
    error,
    // Computed
    isConnected,
    answersList,
    answeredCount,
    hasDiagnostic,
    // Actions
    connectRepository,
    updateReviewedSignals,
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
