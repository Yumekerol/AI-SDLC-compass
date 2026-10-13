import type { ConnectPayload } from '@/types/common'
import type {
  BackendCreateSessionResponse,
  BackendSessionStatusResponse,
  BackendUploadZipResponse,
  BackendScanTriggerResponse,
  BackendSignalsResponse,
  BackendPatchSignalsRequest
} from './types'

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'

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
