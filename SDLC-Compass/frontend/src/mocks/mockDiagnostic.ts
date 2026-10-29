import type { DiagnosticReport } from '@/types/diagnostic'

export const mockDiagnosticReport: DiagnosticReport = {
  id: 'diag-atlas-001',
  repoName: 'Atlas Service',
  generatedAt: 'Just now',
  headline: 'Stabilise testing and release practices before scaling AI adoption.',
  executiveSummary:
    'The sample shows a compact FastAPI / React codebase and an eight-person Scrum team exploring AI. Prioritise clear acceptance criteria, verified CI tests and a repeatable release checklist. Keep early AI use bounded, human-reviewed and aligned with data-sharing policy.',
  metrics: {
    highPriorityCount: 3,
    quickWinsCount: 2,
    phasesCoveredCount: 6
  },
  projectProfile: {
    codeFilesSummary: '48 code files · Python 29 · JavaScript 19 · FastAPI · React · Docker · ~6,400 LOC · ~6 modules (est.)',
    teamSummary: '8 members · Scrum · 1 lead · 4 developers · 2 QA · 1 delivery manager · 7 selected pain points',
    aiMaturitySummary: 'Exploratory · Copilot pilot · ChatGPT for non-code drafting · No systematic adoption declared',
    qualitySummary: '14.3% file-ratio proxy · 6 test files / 42 source files · Executed coverage not measured · Monitoring evidence incomplete'
  },
  evidenceGapAlert: {
    title: 'Resolve evidence gaps before acting',
    description:
      'The team expects CI tests, but build.yml contains no detected test job. Monitoring is self-declared as external, while repository telemetry signals are missing. Validate both boundaries; absence of evidence is not evidence of absence.'
  },
  phases: {
    requirements: {
      phase: 'requirements',
      title: 'Requirements',
      recommendations: [
        {
          id: 'rec-req-1',
          phase: 'requirements',
          title: 'Make acceptance criteria testable before coding starts',
          priority: 'high',
          effort: 'Low - One-team pilot in the next sprint',
          expectedImpact: 'Clearer stories; less ambiguity and avoidable rework.',
          justification: 'README.md provides setup guidance, not a requirements baseline. Team input: ambiguous acceptance criteria; Scrum, 8 members.',
          actionText: 'Introduce a shared story template and use ChatGPT for non-code drafting to turn user stories into testable acceptance criteria with edge cases before implementation begins.',
          repositoryEvidence: 'README.md provides setup guidance, not a requirements baseline.',
          teamInput: 'Ambiguous acceptance criteria; Scrum, 8 members.',
          examplePractice: 'Shared story template + ChatGPT for non-code drafting. Add edge cases and human sign-off to Definition of Ready.',
          quickWin: true
        }
      ]
    },
    testing: {
      phase: 'testing',
      title: 'Testing',
      recommendations: [
        {
          id: 'rec-test-1',
          phase: 'testing',
          title: 'Establish a verified CI test gate, then expand regression tests',
          priority: 'high',
          effort: 'Medium - Validate pipeline, then add a test slice',
          expectedImpact: 'More repeatable regression checks and stronger release confidence.',
          justification: '6 test files / 42 source files = 14.3% file-ratio proxy. build.yml has no detected test step. Team input: manual regression and low CI test confidence.',
          actionText: 'Add automated pytest and Vitest jobs to the CI delivery pipeline, and establish an AI-assisted test generation pilot for critical-path regression suites.',
          repositoryEvidence: '6 test files / 42 source files = 14.3% file-ratio proxy. build.yml has no detected test step.',
          teamInput: 'Manual regression and low CI test confidence.',
          examplePractice: 'Add pytest and Vitest job to delivery pipeline if no external gate exists, then use AI-assisted test drafting for a critical-path regression suite.',
          quickWin: false
        }
      ]
    },
    deployment: {
      phase: 'deployment',
      title: 'Deployment',
      recommendations: [
        {
          id: 'rec-dep-1',
          phase: 'deployment',
          title: 'Turn the release checklist into a repeatable delivery gate',
          priority: 'high',
          effort: 'Medium - Runbook before pipeline expansion',
          expectedImpact: 'Fewer missed release steps and clearer rollback readiness.',
          justification: 'Dockerfile and build.yml present; no deployment job detected in the reviewed repository. Team input: manual release checklist.',
          actionText: 'Convert manual release steps into a versioned container release checklist with automated staging smoke tests and rollback validation.',
          repositoryEvidence: 'Dockerfile and build.yml present; no deployment job detected in the reviewed repository.',
          teamInput: 'Manual release checklist; deployment coordination overhead.',
          examplePractice: 'Versioned Docker image, GitHub Actions release checklist and a staging smoke test. AI may draft release notes from approved changes.',
          quickWin: false
        }
      ]
    },
    design: {
      phase: 'design',
      title: 'Design',
      recommendations: [
        {
          id: 'rec-des-1',
          phase: 'design',
          title: 'Capture architectural decisions in lightweight ADRs',
          priority: 'medium',
          effort: 'Low - Template first, then one decision',
          expectedImpact: 'More traceable trade-offs and easier onboarding.',
          justification: 'README.md found; no architecture document detected. FastAPI + React declared in manifests. Team input: undocumented decisions.',
          actionText: 'Document key architectural decisions and technology trade-offs using lightweight Markdown ADRs stored directly in the repository.',
          repositoryEvidence: 'README.md found; no architecture document detected. FastAPI + React declared in manifests.',
          teamInput: 'Undocumented decisions; review session notes not linked to code.',
          examplePractice: 'docs/adr/ with context, options, decision and consequences. Review in PR; use Mermaid for simple architecture diagrams.',
          quickWin: true
        }
      ]
    },
    development: {
      phase: 'development',
      title: 'Development',
      recommendations: [
        {
          id: 'rec-dev-1',
          phase: 'development',
          title: 'Constrain the Copilot pilot to repeatable, reviewable tasks',
          priority: 'medium',
          effort: 'Medium - Agree guardrails and pilot tasks',
          expectedImpact: 'Less repetitive work without weakening code review.',
          justification: 'api/requirements.txt and web/package.json declare FastAPI, React and Vite. Team input: repetitive implementation; exploratory Copilot use.',
          actionText: 'Define clear boundaries and prompt guidelines for GitHub Copilot, focusing on boilerplate handlers and component scaffolding under peer review.',
          repositoryEvidence: 'api/requirements.txt and web/package.json declare FastAPI, React and Vite.',
          teamInput: 'Repetitive implementation; exploratory Copilot use.',
          examplePractice: 'A prompt checklist for FastAPI handlers and React components. Use GitHub Copilot within approved organisational policy.',
          quickWin: false
        }
      ]
    },
    monitoring: {
      phase: 'monitoring',
      title: 'Monitoring',
      recommendations: [
        {
          id: 'rec-mon-1',
          phase: 'monitoring',
          title: 'Map external telemetry before adding AI-assisted triage',
          priority: 'low',
          effort: 'Medium - Discovery first; priority is provisional',
          expectedImpact: 'More actionable alerts and a safer foundation for triage assistance.',
          justification: 'No telemetry or alert configuration detected in the 48-file repository scope. Team input: noisy alerts; monitoring is managed outside the repository.',
          actionText: 'Audit and map existing external telemetry and alerting sources before piloting AI-assisted incident summarisation.',
          repositoryEvidence: 'No telemetry or alert configuration detected in the 48-file repository scope.',
          teamInput: 'Noisy alerts; monitoring is managed outside the repository.',
          examplePractice: 'Review existing dashboards; consider OpenTelemetry and Grafana only if gaps are confirmed. Pilot incident summarisation with redacted inputs.',
          quickWin: false
        }
      ]
    }
  },
  scopeAndLimitations: {
    currentPocScope: [
      'Approximately 50 code files; Python, JavaScript and Java. Git URL or ZIP source.',
      'Excludes node_modules, .git, binaries and generated files.',
      'Team context is self-declared; repository quality indicators are estimates and were not executed.',
      'LOC, modules and complexity are illustrative, unvalidated estimates. Human review is required before adoption.',
      'Code is temporarily processed and deleted after scanning. Extracted signals are shared with the AI service; code excerpts require approval. Full source code is not shared.'
    ],
    enterpriseRoadmap: [
      'Direct Jira and Azure DevOps integrations, eliminating manual context entry.',
      'Enterprise monorepo and large repository chunking with vector embeddings.',
      'Automated code linters and test runner execution sandbox.',
      'Multi-team portfolio benchmarks and progress tracking.'
    ]
  }
}
