import type { RepoSignals } from '@/types/signals'
import type { BackendSignalsResponse, BackendPatchSignalsRequest } from './types'

/**
 * Transforms FastAPI backend scanner response into the frontend RepoSignals model.
 */
export function adaptBackendSignalsToRepoSignals(raw: BackendSignalsResponse): RepoSignals {
  const groups = raw.signal_groups || {}
  const langData = groups.languages?.data
  const sizeData = groups.size_and_structure?.data
  const stackData = groups.stack_and_tooling?.data
  const cicdData = groups.cicd_and_operations?.data
  const qualityData = groups.quality_indicators?.data
  const warningsData = groups.warnings_and_gaps?.data

  // Languages breakdown
  const languages =
    langData?.breakdown?.map((item) => ({
      name: item.language,
      files: item.files,
      percentage: Math.round(item.percentage)
    })) || []

  // Size and structure
  const codeFiles = sizeData?.code_files ?? 0
  const locEstimate = sizeData?.loc_estimate ?? 0
  const moduleEstimate = sizeData?.module_estimate ?? 0

  let approxComplexity: 'Low' | 'Moderate' | 'High' = 'Low'
  if (codeFiles > 80 || locEstimate > 12000) {
    approxComplexity = 'High'
  } else if (codeFiles > 30 || locEstimate > 4000) {
    approxComplexity = 'Moderate'
  }

  const size = {
    codeFiles,
    locEstimate,
    moduleEstimate,
    approxComplexity,
    confidence: `${capitalize(groups.size_and_structure?.confidence || 'mixed')} confidence · ${groups.size_and_structure?.confidence_source || 'Inventory estimates'}`,
    evidenceSummary:
      groups.size_and_structure?.evidence_paths?.slice(0, 3).join(' · ') ||
      'Derived from file extension inventory and lines of code estimates.'
  }

  // Stack & tooling
  const stack = {
    frameworks: stackData?.frameworks || [],
    testingLibraries: stackData?.testing_libraries || [],
    buildTools: stackData?.build_tools || [],
    sampleEvidence:
      groups.stack_and_tooling?.evidence_paths?.slice(0, 3).join(' · ') ||
      'Dependency manifests and build descriptors'
  }

  // CI/CD & operations
  const cicd = {
    ciProvider: cicdData?.cicd_tool || 'None detected',
    hasBuildJob: cicdData?.has_containerization || Boolean(cicdData?.cicd_tool),
    hasTestJob: cicdData?.has_test_step_in_ci ?? false,
    hasDeployJob: cicdData?.has_deploy_step_in_ci ?? false,
    containerization: cicdData?.has_containerization
      ? cicdData.dockerfile_path
        ? `Dockerfile present (${cicdData.dockerfile_path})`
        : 'Dockerfile present'
      : 'No Dockerfile detected',
    documentation: cicdData?.has_documentation
      ? cicdData.documentation_notes || 'Documentation present'
      : 'No architecture document found',
    sampleEvidence:
      groups.cicd_and_operations?.evidence_paths?.slice(0, 3).join(' · ') ||
      'Workflow files and repository configs'
  }

  // Quality indicators
  const testFilesCount = qualityData?.test_file_count ?? 0
  const sourceFilesCount = qualityData?.source_file_count ?? 0
  const testToCodeRatio =
    qualityData?.test_to_code_file_ratio ??
    (sourceFilesCount > 0 ? parseFloat(((testFilesCount / sourceFilesCount) * 100).toFixed(1)) : 0)

  const executedCoverage =
    qualityData?.executed_coverage !== null && qualityData?.executed_coverage !== undefined
      ? `${qualityData.executed_coverage}%`
      : 'Not measured'

  const qualityGateStatus = qualityData?.has_quality_gate
    ? 'Quality gate configured'
    : qualityData?.quality_gate_notes || 'No enforced test gate detected in CI'

  const quality = {
    testToCodeRatio,
    testFilesCount,
    sourceFilesCount,
    executedCoverage,
    qualityGateStatus,
    sampleEvidence:
      groups.quality_indicators?.evidence_paths?.slice(0, 3).join(' · ') ||
      `${testFilesCount} test files / ${sourceFilesCount} source files`
  }

  // Warnings & gaps
  const warnings =
    warningsData?.warnings?.map((w, index) => ({
      id: `w-${index + 1}`,
      title: w.title,
      description: w.description,
      severity: 'warning' as const,
      sampleEvidence: groups.warnings_and_gaps?.evidence_paths?.[index] || groups.warnings_and_gaps?.evidence_paths?.[0]
    })) || []

  const isEligible = raw.scope?.eligible_for_poc ?? true
  const eligibleReason = isEligible
    ? 'Eligible for PoC: Supported files detected within limit'
    : raw.scope?.scope_warnings?.[0] || 'Repository exceeds PoC boundaries'

  return {
    sessionId: raw.session_id,
    repoName: raw.repository?.name || 'Repository',
    repoUrl: raw.repository?.clone_url || undefined,
    commitHash: raw.repository?.commit_hash || undefined,
    status: 'scanned',
    isEligiblePoC: isEligible,
    eligibleReason,
    totalSupportedFiles: raw.scope?.supported_code_files ?? codeFiles,
    excludedItemsCount: raw.scope?.excluded_items ?? 0,
    languages,
    size,
    stack,
    cicd,
    quality,
    warnings
  }
}

/**
 * Transforms updated RepoSignals into the backend PATCH payload format.
 */
export function adaptRepoSignalsToPatchRequest(signals: RepoSignals): BackendPatchSignalsRequest {
  return {
    signal_groups: {
      languages: {
        data: {
          breakdown: signals.languages.map((l) => ({
            language: l.name,
            files: l.files,
            percentage: l.percentage
          }))
        }
      },
      size_and_structure: {
        data: {
          code_files: signals.size.codeFiles,
          loc_estimate: signals.size.locEstimate,
          module_estimate: signals.size.moduleEstimate
        }
      },
      stack_and_tooling: {
        data: {
          frameworks: signals.stack.frameworks,
          testing_libraries: signals.stack.testingLibraries,
          build_tools: signals.stack.buildTools
        }
      },
      cicd_and_operations: {
        data: {
          cicd_tool: signals.cicd.ciProvider,
          has_test_step_in_ci: signals.cicd.hasTestJob,
          has_deploy_step_in_ci: signals.cicd.hasDeployJob
        }
      },
      quality_indicators: {
        data: {
          test_file_count: signals.quality.testFilesCount,
          source_file_count: signals.quality.sourceFilesCount,
          test_to_code_file_ratio: signals.quality.testToCodeRatio
        }
      }
    }
  }
}

function capitalize(text: string): string {
  if (!text) return ''
  return text.charAt(0).toUpperCase() + text.slice(1)
}
