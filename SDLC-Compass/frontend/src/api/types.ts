/**
 * Backend API Data Contracts
 * Defines payloads and responses from FastAPI endpoints.
 */

export interface BackendCreateSessionRequest {
  source_type: 'git' | 'zip'
  git_url?: string | null
  access_token?: string | null
  consent_given: boolean
}

export interface BackendCreateSessionResponse {
  session_id: string
  status: string
  created_at: string
}

export interface BackendSessionStatusResponse {
  session_id: string
  status: 'created' | 'ingesting' | 'scanning' | 'awaiting_signal_review' | 'awaiting_team_context' | 'analyzing' | 'synthesizing' | 'complete' | 'error'
  source_type: 'git' | 'zip'
  git_url?: string | null
  created_at: string
  updated_at?: string | null
  signals_confirmed: boolean
  report_ready: boolean
  error_message?: string | null
}

export interface BackendUploadZipResponse {
  session_id: string
  filename: string
  status: string
  workspace_path: string
}

export interface BackendScanTriggerResponse {
  session_id: string
  status: string
  scan_started_at: string
  estimated_duration_ms: number
}

export interface BackendLanguageBreakdown {
  language: string
  files: number
  percentage: number
}

export interface BackendLanguagesGroup {
  confidence: string
  confidence_source: string
  data: {
    primary_language?: string | null
    breakdown?: BackendLanguageBreakdown[]
  }
  evidence_paths?: string[]
  user_edited?: boolean
}

export interface BackendSizeGroup {
  confidence: string
  confidence_source: string
  data: {
    code_files?: number
    total_files?: number
    loc_estimate?: number
    module_estimate?: number
    avg_file_size_loc?: number
  }
  evidence_paths?: string[]
  user_edited?: boolean
}

export interface BackendStackGroup {
  confidence: string
  confidence_source: string
  data: {
    frameworks?: string[]
    testing_libraries?: string[]
    build_tools?: string[]
    linters?: string[]
    formatters?: string[]
    databases?: string[]
    package_managers?: string[]
  }
  evidence_paths?: string[]
  user_edited?: boolean
}

export interface BackendCicdGroup {
  confidence: string
  confidence_source: string
  data: {
    cicd_tool?: string | null
    cicd_description?: string | null
    has_containerization?: boolean
    dockerfile_path?: string | null
    has_documentation?: boolean
    documentation_notes?: string | null
    has_test_step_in_ci?: boolean
    has_deploy_step_in_ci?: boolean
    has_monitoring_config?: boolean
    monitoring_tools?: string[]
    has_iac?: boolean
    iac_tools?: string[]
  }
  evidence_paths?: string[]
  user_edited?: boolean
}

export interface BackendQualityGroup {
  confidence: string
  confidence_source: string
  data: {
    test_to_code_file_ratio?: number | null
    test_file_count?: number
    source_file_count?: number
    executed_coverage?: number | null
    has_quality_gate?: boolean
    quality_gate_notes?: string | null
    has_code_style_config?: boolean
    code_style_tools?: string[]
  }
  evidence_paths?: string[]
  user_edited?: boolean
}

export interface BackendWarningItem {
  category: string
  title: string
  description: string
}

export interface BackendWarningsGroup {
  confidence: string
  confidence_source: string
  data: {
    warnings?: BackendWarningItem[]
  }
  evidence_paths?: string[]
  user_edited?: boolean
}

export interface BackendSignalsResponse {
  session_id: string
  repository?: {
    name?: string
    branch?: string | null
    commit_hash?: string | null
    source_type?: string
    clone_url?: string | null
  }
  scope?: {
    eligible_for_poc?: boolean
    supported_code_files?: number
    excluded_items?: number
    exclusion_rules?: string[]
    scope_warnings?: string[]
  }
  signal_groups: {
    languages?: BackendLanguagesGroup
    size_and_structure?: BackendSizeGroup
    stack_and_tooling?: BackendStackGroup
    cicd_and_operations?: BackendCicdGroup
    quality_indicators?: BackendQualityGroup
    warnings_and_gaps?: BackendWarningsGroup
  }
}

export interface BackendPatchSignalsRequest {
  signal_groups: Record<string, { data: Record<string, unknown> }>
}

// ─── Batch 2: Diagnostic Conversation & Report ────────────────────────

export interface BackendDiagnosticQuestion {
  question_id: string
  text: string
  priority: string
  tdm_field: string
  answered?: boolean
  answer?: string | null
}

export interface BackendConversationMessage {
  id: string
  role: 'supervisor' | 'agent' | 'user'
  agent_domain?: string | null
  agent_label?: string | null
  content: string
  questions?: BackendDiagnosticQuestion[]
  timestamp: string
}

export interface BackendDiagnoseResponse {
  session_id: string
  status: string
  processing: boolean
  // Just the welcome message — the actual specialist pipeline runs in the
  // background. Poll getConversation / pollConversation for what follows.
  initial_messages: BackendConversationMessage[]
  agent_statuses?: Record<string, { status: string; progress: number }>
}

export interface BackendConversationResponse {
  session_id: string
  messages: BackendConversationMessage[]
  agent_statuses: Record<string, { status: string; progress: number }>
  // true while a specialist run / resume / synthesis is in flight on the
  // backend for this session. pollConversation waits for this to go false.
  processing: boolean
  status: string
  error_message?: string | null
}

export interface BackendSendMessageRequest {
  content: string
  responding_to_questions?: string[]
}

export interface BackendSendMessageResponse {
  session_id: string
  processing: boolean
  agent_statuses: Record<string, { status: string; progress: number }>
}

export interface BackendKnowledgeGapsResponse {
  session_id: string
  gaps: Record<string, string[]>
}

export interface BackendAdvisorMessagesResponse {
  session_id: string
  messages: BackendConversationMessage[]
}

export interface BackendContinueDiagnosticResponse {
  session_id: string
  status: string
  report_ready: boolean
}

export interface BackendReadinessScore {
  domain: string
  domain_label: string
  readiness_score: number
  opportunity_score: number
  readiness_label: string
  verdict: string
}

export interface BackendRecommendation {
  id: string
  title: string
  domain: string
  description: string
  effort: string
  impact: string
  risk_level: string
  prerequisites?: string[]
  ai_relevance?: string
  is_foundation?: boolean
}

export interface BackendRecommendationPhase {
  phase_label: string
  phase_description: string
  estimated_effort: string
  recommendations: BackendRecommendation[]
}

export interface BackendSynthesisOutput {
  session_id: string
  generated_at?: string
  repository?: {
    name?: string
    branch?: string
    commit_hash?: string
    languages?: string[]
    frameworks?: string[]
  }
  executive_summary?: {
    headline?: string
    overall_readiness?: string
    overall_readiness_score?: number
    summary_text?: string
  }
  readiness_scorecard?: Record<string, BackendReadinessScore>
  phased_recommendations?: {
    phase_1_foundation?: BackendRecommendationPhase
    phase_2_quick_wins?: BackendRecommendationPhase
    phase_3_advanced?: BackendRecommendationPhase
  }
  knowledge_gaps_summary?: {
    total_resolved?: number
    total_asked?: number
    unresolved_gaps?: Array<Record<string, unknown>>
  }
  disclaimers?: {
    scope?: string
    accuracy?: string
    affiliation?: string
  }
}

