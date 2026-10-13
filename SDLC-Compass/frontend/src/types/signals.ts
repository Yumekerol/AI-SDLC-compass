export interface LanguageSignal {
  name: string
  files: number
  percentage: number
}

export interface SizeSignal {
  codeFiles: number
  locEstimate: number
  moduleEstimate: number
  approxComplexity: 'Low' | 'Moderate' | 'High'
  confidence: string
  evidenceSummary: string
}

export interface StackSignal {
  frameworks: string[]
  testingLibraries: string[]
  buildTools: string[]
  sampleEvidence: string
}

export interface CiCdSignal {
  ciProvider: string
  hasBuildJob: boolean
  hasTestJob: boolean
  hasDeployJob: boolean
  containerization: string
  documentation: string
  sampleEvidence: string
}

export interface QualitySignal {
  testToCodeRatio: number
  testFilesCount: number
  sourceFilesCount: number
  executedCoverage: string
  qualityGateStatus: string
  sampleEvidence: string
}

export interface WarningSignal {
  id: string
  title: string
  description: string
  severity: 'warning' | 'info' | 'danger'
  sampleEvidence?: string
}

export interface RepoSignals {
  sessionId?: string
  repoName: string
  repoUrl?: string
  commitHash?: string
  status: 'scanned' | 'scanning' | 'error'
  isEligiblePoC: boolean
  eligibleReason: string
  totalSupportedFiles: number
  excludedItemsCount: number
  languages: LanguageSignal[]
  size: SizeSignal
  stack: StackSignal
  cicd: CiCdSignal
  quality: QualitySignal
  warnings: WarningSignal[]
}
