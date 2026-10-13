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
