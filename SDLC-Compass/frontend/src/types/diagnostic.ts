export type SdlcPhase =
  | 'requirements'
  | 'design'
  | 'development'
  | 'testing'
  | 'deployment'
  | 'monitoring'

export type RecommendationPriority = 'high' | 'medium' | 'low'

export interface Recommendation {
  id: string
  phase: SdlcPhase
  title: string
  priority: RecommendationPriority
  effort: string
  expectedImpact: string
  justification: string
  examplePractice: string
  quickWin: boolean
}

export interface PhaseReportSection {
  phase: SdlcPhase
  title: string
  recommendations: Recommendation[]
}

export interface DiagnosticReport {
  id: string
  repoName: string
  generatedAt: string
  headline: string
  executiveSummary: string
  metrics: {
    highPriorityCount: number
    quickWinsCount: number
    phasesCoveredCount: number
  }
  projectProfile: {
    codeFilesSummary: string
    teamSummary: string
    aiMaturitySummary: string
    qualitySummary: string
  }
  evidenceGapAlert?: {
    title: string
    description: string
  }
  phases: Record<SdlcPhase, PhaseReportSection>
  scopeAndLimitations: {
    currentPocScope: string[]
    enterpriseRoadmap: string[]
  }
}
