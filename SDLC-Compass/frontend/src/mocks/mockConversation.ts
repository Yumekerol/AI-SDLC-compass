import type { BackendConversationMessage } from '@/api/types'

/** Step 3 sample conversation, shown only in mock mode (VITE_USE_MOCKS). */
export const mockConversation: BackendConversationMessage[] = [
  {
    id: 'mock-sup-1',
    role: 'supervisor',
    content:
      "I've completed the deterministic code scan. Our four domain specialists will now review the repository and may ask you a few clarifying questions as they go.",
    timestamp: '2026-01-01T09:41:00Z'
  },
  {
    id: 'mock-req-1',
    role: 'agent',
    agent_domain: 'requirements_design',
    agent_label: 'Requirements & Design',
    content:
      'Are acceptance criteria documented consistently, and are design decisions captured somewhere the team can reference?',
    timestamp: '2026-01-01T09:42:00Z'
  },
  {
    id: 'mock-user-1',
    role: 'user',
    content: 'Acceptance criteria live in tickets; design decisions are mostly in review notes and not linked back.',
    timestamp: '2026-01-01T09:43:00Z'
  },
  {
    id: 'mock-qa-1',
    role: 'agent',
    agent_domain: 'qa_testing',
    agent_label: 'QA & Testing',
    content: 'Are the existing test files mostly unit, integration or end-to-end tests?',
    timestamp: '2026-01-01T09:46:00Z'
  }
]
