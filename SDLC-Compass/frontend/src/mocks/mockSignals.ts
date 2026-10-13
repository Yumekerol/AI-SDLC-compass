import type { RepoSignals } from '@/types/signals'

export const mockRepoSignals: RepoSignals = {
  repoName: 'Atlas Service',
  repoUrl: 'https://github.com/sample/atlas-service.git',
  commitHash: 'a8f2c10',
  status: 'scanned',
  isEligiblePoC: true,
  eligibleReason: 'Eligible for PoC: Python & JavaScript detected within supported file limit',
  totalSupportedFiles: 48,
  excludedItemsCount: 212,
  languages: [
    { name: 'Python', files: 29, percentage: 60 },
    { name: 'JavaScript', files: 19, percentage: 40 }
  ],
  size: {
    codeFiles: 48,
    locEstimate: 6400,
    moduleEstimate: 6,
    approxComplexity: 'Moderate',
    confidence: 'Mixed confidence · Counts + estimates',
    evidenceSummary: 'LOC, module boundaries and complexity are illustrative estimates from repository inventory (api/app/*, web/src/*, tests/*).'
  },
  stack: {
    frameworks: ['FastAPI', 'React'],
    testingLibraries: ['pytest', 'Vitest'],
    buildTools: ['Vite', 'pip'],
    sampleEvidence: 'api/requirements.txt · web/package.json · pyproject.toml'
  },
  cicd: {
    ciProvider: 'GitHub Actions',
    hasBuildJob: true,
    hasTestJob: false,
    hasDeployJob: false,
    containerization: 'Dockerfile present',
    documentation: 'README present · No architecture document found',
    sampleEvidence: '.github/workflows/build.yml · Dockerfile · README.md'
  },
  quality: {
    testToCodeRatio: 14.3,
    testFilesCount: 6,
    sourceFilesCount: 42,
    executedCoverage: 'Not measured',
    qualityGateStatus: 'No enforced test gate detected in CI',
    sampleEvidence: '6 test files / 42 source files · tests/ · web/src/*.test.js'
  },
  warnings: [
    {
      id: 'w-1',
      title: 'Monitoring visibility is incomplete',
      description: 'No telemetry or alert configuration detected. Monitoring may live outside this repository.',
      severity: 'warning',
      sampleEvidence: 'No monitoring config found in reviewed scope · build.yml'
    },
    {
      id: 'w-2',
      title: 'Test tools present; CI test step absent',
      description: 'Confirm whether tests run in another pipeline before treating this as a delivery gap.',
      severity: 'warning',
      sampleEvidence: '.github/workflows/build.yml'
    }
  ]
}
