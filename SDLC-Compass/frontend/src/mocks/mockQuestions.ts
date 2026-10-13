import type { Question, TopicProgress } from '@/types/questions'

export const mockQuestions: Question[] = [
  {
    id: 'q-1',
    topic: 'Requirements & Design',
    supervisorIntro: 'Atlas Service has 48 code files, FastAPI + React, 6 test files, and a build.yml with a build job but no detected test or deploy job. We will start with ways of working and pain points.',
    agentName: 'Requirements & Design Specialist',
    agentRole: 'Requirements & Design',
    text: 'Can you confirm whether acceptance criteria are documented consistently across the team and whether design decisions are captured somewhere the delivery team can reference?',
    suggestionChips: [
      { id: 'c-1-1', label: 'Scrum with Jira stories', value: 'We use Scrum with Jira stories. Acceptance criteria are usually in Jira, but design decisions are often in notes from review sessions.' },
      { id: 'c-1-2', label: 'Documented in PRs & lightweight notes', value: 'We capture design decisions in PR notes and meeting transcripts, but acceptance criteria vary by team member.' },
      { id: 'c-1-3', label: 'Strict Gherkin / BDD criteria', value: 'We have strict Gherkin criteria in Jira, and ADRs in git for architectural decisions.' },
      { id: 'c-1-4', label: 'Informal / shifting requirements', value: 'Requirements are mostly informal and communicated via Slack; design decisions are rarely documented.' }
    ],
    placeholder: 'Add details about your backlog, sprint cadence, or how design decisions are agreed...'
  },
  {
    id: 'q-2',
    topic: 'Code & Refactoring',
    agentName: 'Code & Refactoring Specialist',
    agentRole: 'Code & Refactoring',
    text: 'You mentioned repetitive implementation. Is that mostly in the Python service, the React frontend, or both? Are there any areas where the team feels the codebase is already too complex to refactor without more evidence?',
    suggestionChips: [
      { id: 'c-2-1', label: 'Repetitive FastAPI boilerplate', value: 'Repetitive implementation is visible mostly in the Python FastAPI boilerplate and CRUD validation.' },
      { id: 'c-2-2', label: 'Frontend component boilerplate', value: 'Mainly in the React frontend forms and UI state handlers; backend is relatively stable.' },
      { id: 'c-2-3', label: 'Both Python & React', value: 'Repetitive boilerplate exists across both the Python service and React components. We want AI for scaffold generation.' },
      { id: 'c-2-4', label: 'Legacy modules need safe tests first', value: 'The codebase has legacy modules that are too risky to touch without adding regression tests first.' }
    ],
    placeholder: 'Describe where boilerplate is highest or where refactoring feels risky...'
  },
  {
    id: 'q-3',
    topic: 'QA & Testing',
    agentName: 'QA & Testing Specialist',
    agentRole: 'QA & Testing',
    text: 'Are the 6 test files mostly unit tests, integration tests, or end-to-end tests? Does the team rely on any external testing workflows that are not visible in this repository?',
    suggestionChips: [
      { id: 'c-3-1', label: 'Local unit tests only', value: 'The 6 files are unit and integration tests run locally with pytest and vitest. CI does not enforce them yet.' },
      { id: 'c-3-2', label: 'External QA pipeline exists', value: 'We have an external automated QA pipeline in Jenkins that runs nightly regression tests.' },
      { id: 'c-3-3', label: 'Manual QA before release', value: 'We rely heavily on manual QA verification before releasing to production, which slows delivery down.' },
      { id: 'c-3-4', label: 'Tests exist but run irregularly', value: 'Tests exist but are flaky and run irregularly, so the team lacks confidence in them.' }
    ],
    placeholder: 'Explain how testing is validated before releasing code...'
  },
  {
    id: 'q-4',
    topic: 'DevOps & Monitoring',
    agentName: 'DevOps & Monitoring Specialist',
    agentRole: 'DevOps & Monitoring',
    text: 'Is the manual release checklist used for every deployment, or only for production? Are there any external monitoring dashboards or alerting rules that the diagnostic should reference?',
    suggestionChips: [
      { id: 'c-4-1', label: 'Checklist for production only', value: 'The checklist is mainly used for production. Monitoring lives in an external Datadog dashboard outside this repo.' },
      { id: 'c-4-2', label: 'Manual release every time', value: 'Manual release checklist is executed for every environment deployment. Alerting is noisy and unmapped.' },
      { id: 'c-4-3', label: 'Automated staging, manual prod', value: 'Staging is automated via Docker, but production requires sign-offs and manual verification.' },
      { id: 'c-4-4', label: 'No centralized telemetry yet', value: 'We do not have centralized telemetry or alerts yet; errors are identified from user reports.' }
    ],
    placeholder: 'Clarify deployment frequency and where monitoring is hosted...'
  }
]

export const mockInitialTopics: TopicProgress[] = [
  { id: 'topic-1', name: 'Requirements & Design', status: 'current' },
  { id: 'topic-2', name: 'Code & Refactoring', status: 'pending' },
  { id: 'topic-3', name: 'QA & Testing', status: 'pending' },
  { id: 'topic-4', name: 'DevOps & Monitoring', status: 'pending' }
]
