export type ErrorType = 'network' | 'ai_down' | 'out_of_scope'

export interface AppError {
  type: ErrorType
  title: string
  message: string
  details?: string
  canRetry: boolean
  retryActionName?: string
}

export interface StepItem {
  number: number
  key: string
  title: string
  route: string
}

export type ScanSource = 'git' | 'zip'

export interface ConnectPayload {
  source: ScanSource
  gitUrl?: string
  file?: File
}
