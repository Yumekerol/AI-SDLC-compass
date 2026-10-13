export type SdlcPhase =
  | 'requirements'
  | 'design'
  | 'development'
  | 'testing'
  | 'deployment'
  | 'monitoring'
  | 'requirements_design'
  | 'code_refactoring'
  | 'qa_testing'
  | 'devops_monitoring'
  | 'deployment_monitoring'

export type RecommendationPriority = 'high' | 'medium' | 'low'

export interface Recommendation {
  id: string
  phase: SdlcPhase | string
  title: string
  priority: RecommendationPriority
  effort: string
  expectedImpact: string
  justification: string
  examplePractice: string
  quickWin: boolean
}

export interface PhaseReportSection {
  phase: SdlcPhase | string
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
  phases: Record<string, PhaseReportSection>
  scopeAndLimitations: {
    currentPocScope: string[]
    enterpriseRoadmap: string[]
  }
}
