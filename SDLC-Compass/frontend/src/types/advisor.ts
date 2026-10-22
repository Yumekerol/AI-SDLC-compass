export interface AdvisorMessage {
  id: string
  sender: 'advisor' | 'user' | 'specialist'
  senderName: string
  role?: string
  content: string
  timestamp: string
  statusChangeProposal?: {
    title: string
    reason: string
    status: 'pending' | 'applied'
  }
}

export interface UnresolvedKnowledgeGap {
  id: string
  title: string
  description: string
  status: 'Open' | 'Resolved'
}

export interface SpecialistActivity {
  id: string
  phase: string
  title: string
  status: 'Analyzing' | 'Idle' | 'Updated'
  evidenceTokens: string[]
  description: string
  capacityPercent?: number
}

export interface AdvisorContext {
  repoName: string
  summaryStats: string
  teamMethodology: string
  aiStartingPoint: string
  painPointsCount: number
  currentTools: string[]
  specialists: SpecialistActivity[]
  unresolvedGaps: UnresolvedKnowledgeGap[]
  suggestedQuestions: string[]
}
