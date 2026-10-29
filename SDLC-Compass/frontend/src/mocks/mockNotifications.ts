import type { AppNotification } from '@/types/notifications'

const now = Date.now()

export const mockNotifications: AppNotification[] = [
  {
    id: 'notif-1',
    type: 'report_ready',
    level: 'success',
    title: 'Report ready for review',
    message: 'The current version of the report is available for review by the supervisor and synthesizer.',
    domain: 'QA',
    route_hint: '/report',
    action_label: 'See report →',
    created_at: new Date(now - 2 * 60 * 1000).toISOString(),
    read: false
  },
  {
    id: 'notif-2',
    type: 'specialist_question',
    level: 'warning',
    title: 'Repository size reviewed',
    message: 'The Atlas Service repository has 48 code files and 6 declared tests; the coverage boundary requires team validation.',
    domain: 'Requirements',
    route_hint: '/context',
    action_label: 'See context →',
    created_at: new Date(now - 18 * 60 * 1000).toISOString(),
    read: false
  },
  {
    id: 'notif-3',
    type: 'scan_failed',
    level: 'error',
    title: 'Lack of evidence for CI',
    message: 'The build.yml file does not contain a detectable test job; manual confirmation of automated CI pipeline is recommended.',
    domain: 'DevOps',
    route_hint: '/signals',
    action_label: 'See evidence →',
    created_at: new Date(now - 60 * 60 * 1000).toISOString(),
    read: false
  },
  {
    id: 'notif-4',
    type: 'specialist_question',
    level: 'warning',
    title: 'Clarifying sprint cadence',
    message: 'Requirements specialist asked for confirmation on the team sprint cadence and release review frequency.',
    domain: 'Requirements',
    route_hint: '/report',
    action_label: 'Reply in chat →',
    created_at: new Date(now - 2 * 60 * 60 * 1000).toISOString(),
    read: false
  },
  {
    id: 'notif-5',
    type: 'scan_complete',
    level: 'success',
    title: 'Repository scan complete',
    message: 'Light scanner completed indexing 48 code files, 6 signal groups and architecture boundaries.',
    domain: 'System',
    route_hint: '/signals',
    action_label: 'Review signals →',
    created_at: new Date(now - 3 * 60 * 60 * 1000).toISOString(),
    read: false
  }
]

