export type NotificationType =
  | 'scan_complete'
  | 'scan_failed'
  | 'specialist_question'
  | 'report_ready'
  | string

export type NotificationLevel = 'info' | 'success' | 'warning' | 'error'

export interface AppNotification {
  id: string
  type: NotificationType
  level: NotificationLevel
  title: string
  message: string
  domain?: string | null
  route_hint?: string | null
  created_at: string
  read: boolean
  action_label?: string
}

