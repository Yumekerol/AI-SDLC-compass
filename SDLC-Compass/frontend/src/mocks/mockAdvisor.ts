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
      evidenceTokens: ['Jira - notes', 'review sessions', 'ambiguous criteria'],
      description: 'Examining acceptance criteria coverage, design review cadence and decision documentation.'
    },
    {
      id: 'spec-2',
      phase: 'Code & Refactoring',
      title: 'Code & Refactoring',
      status: 'Analyzing',
      evidenceTokens: ['api/app', 'repetitive implementation', 'build.yml'],
      description: 'Reviewing code structure, duplication, and the gap between local test execution and CI workflow coverage.'
    },
    {
      id: 'spec-3',
      phase: 'QA & Testing',
      title: 'QA & Testing',
      status: 'Analyzing',
      evidenceTokens: ['6 test files / 42 source', 'local execution', 'CI gap'],
      description: 'Mapping test presence, regression risk, and the relationship between local test execution and CI workflow coverage.'
    },
    {
      id: 'spec-4',
      phase: 'DevOps & Monitoring',
      title: 'DevOps & Monitoring',
      status: 'Analyzing',
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
    id: 'msg-1',
    sender: 'specialist',
    senderName: 'Supervisor',
    role: 'Gathering context',
    content:
      'Atlas Service has 48 code files, FastAPI + React, 6 test files / 42 source files, and a build.yml with a build job but no detected test or deploy job. We will start with ways of working, pain points and AI readiness.',
    timestamp: '09:41'
  },
  {
    id: 'msg-2',
    sender: 'user',
    senderName: 'Team representative',
    content:
      'Can we keep the release checklist recommendation, but make it the next priority after the CI test gate? We want to automate build checks first, then make the release runbook repeatable.',
    timestamp: '09:43'
  },
  {
    id: 'msg-3',
    sender: 'specialist',
    senderName: 'DevOps & Monitoring',
    role: 'Response',
    content:
      'That makes sense. If the team verifies the CI test gate first, the release checklist can be refined with clearer ownership and rollback steps. I will propose that change.',
    timestamp: '09:44'
  },
  {
    id: 'msg-4',
    sender: 'specialist',
    senderName: 'QA & Testing',
    role: 'Response',
    content:
      'I agree. Once the CI test gate is clearer, the release checklist can be tied to the same pipeline. That reduces the chance of manual release steps being missed.',
    timestamp: '09:45'
  },
  {
    id: 'msg-5',
    sender: 'advisor',
    senderName: 'Synthesizer',
    role: 'Report note',
    content:
      'I updated the prioritisation notes in your working context. The Deployment recommendation now specifies runbook refinement following CI gate establishment.',
    timestamp: '09:46',
    statusChangeProposal: {
      title: 'Swap Deployment priority from High to Medium',
      reason: 'Verify the CI test gate before making the release checklist repeatable.',
      status: 'applied'
    }
  }
]
