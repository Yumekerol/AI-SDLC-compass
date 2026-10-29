import type { AdvisorContext, AdvisorMessage } from '@/types/advisor'

export const mockAdvisorContext: AdvisorContext = {
  repoName: 'Atlas Service',
  summaryStats: '48 code files · FastAPI + React · 6 test files / 42 source files',
  teamMethodology: 'Scrum · 8 members',
  aiStartingPoint: 'Exploratory (Copilot pilot · ChatGPT)',
  painPointsCount: 7,
  currentTools: ['GitHub Copilot pilot', 'ChatGPT'],
  specialists: [
    {
      id: 'spec-1',
      phase: 'Requirements & Design',
      title: 'Requirements & Design',
      status: 'Analyzing',
      capacityPercent: 30,
      evidenceTokens: ['Jira · notes', 'review sessions', 'ambiguous criteria'],
      description: 'Examining acceptance criteria coverage, design review cadence and decision documentation.'
    },
    {
      id: 'spec-2',
      phase: 'Code & Refactoring',
      title: 'Code & Refactoring',
      status: 'Analyzing',
      capacityPercent: 60,
      evidenceTokens: ['api/app', 'repetitive implementation', 'build.yml'],
      description: 'Reviewing code structure, duplication, and the gap between local test execution and CI workflow coverage.'
    },
    {
      id: 'spec-3',
      phase: 'QA & Testing',
      title: 'QA & Testing',
      status: 'Analyzing',
      capacityPercent: 50,
      evidenceTokens: ['6 test files / 42 source', 'local execution', 'CI gap'],
      description: 'Mapping test presence, regression risk, and the relationship between local test execution and CI workflow coverage.'
    },
    {
      id: 'spec-4',
      phase: 'DevOps & Monitoring',
      title: 'DevOps & Monitoring',
      status: 'Analyzing',
      capacityPercent: 70,
      evidenceTokens: ['build.yml', 'release checklist', 'external monitoring'],
      description: 'Examining release process maturity, monitoring visibility, and the relationship between repository signals and external workflows.'
    }
  ],
  unresolvedGaps: [
    {
      id: 'gap-1',
      title: 'CI test execution',
      description: 'Tests run locally, but no test job was detected in build.yml. Confirm whether tests run in another pipeline before treating this as a delivery gap.',
      status: 'Open'
    },
    {
      id: 'gap-2',
      title: 'External monitoring',
      description: 'Monitoring lives outside this repository. Confirm whether external dashboards or alerting rules should be referenced in the diagnostic.',
      status: 'Open'
    },
    {
      id: 'gap-3',
      title: 'Critical business paths',
      description: 'The diagnostic needs to understand which delivery paths are most critical to the business before prioritising recommendations.',
      status: 'Open'
    }
  ],
  suggestedQuestions: [
    'How should we introduce ADRs without adding friction to sprints?',
    'What is the recommended pilot scope for GitHub Copilot in FastAPI?',
    'Can we move the Deployment recommendation to Medium priority?',
    'How do we set up an automated CI test gate with pytest and vitest?'
  ]
}

export const mockInitialAdvisorMessages: AdvisorMessage[] = [
  {
    id: 'msg-sup-user-1',
    sender: 'user',
    senderName: 'Team representative',
    role: 'Question',
    content:
      'Can we keep the release checklist recommendation, but make it the next priority after the CI test gate? We want to automate build checks first, then make the release runbook repeatable.',
    timestamp: '09:43'
  },
  {
    id: 'msg-sup-prop-1',
    sender: 'advisor',
    senderName: 'Synthesizer',
    role: 'Proposal',
    content:
      'Swap Deployment priority from High to Medium. Keep the recommendation, but move it below the CI test gate so the team automates build checks before refining the release runbook.',
    timestamp: '09:44',
    statusChangeProposal: {
      title:
        'Swap Deployment priority from High to Medium. Keep the recommendation, but move it below the CI test gate so the team automates build checks before refining the release runbook.',
      reason:
        'The team wants to verify the CI test gate before making the release checklist repeatable. This keeps the recommendation, but changes the order of delivery.',
      status: 'pending'
    }
  },
  {
    id: 'msg-sup-synth-1',
    sender: 'advisor',
    senderName: 'Synthesizer',
    role: 'Report note',
    content:
      'If approved, this change will update the Deployment recommendation and the report summary. The PDF export will reflect the selected version, not the pending proposal.',
    timestamp: '09:45'
  }
]
