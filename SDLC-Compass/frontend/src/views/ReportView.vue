<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import * as api from '@/api'
import type { DiagnosticReport, RecommendationPriority } from '@/types/diagnostic'
import { mockDiagnosticReport } from '@/mocks'

const router = useRouter()
const store = useSessionStore()

const exportNotice = ref<string>('')
const isExporting = ref<boolean>(false)
const isMock = computed(() => store.isMock)
const reportNotReady = ref<boolean>(false)

// Chat Tab Keys
type TabKey = 'supervisor' | 'requirements' | 'code' | 'testing' | 'devops'

interface ChatTab {
  id: TabKey
  label: string
}

const tabs: ChatTab[] = [
  { id: 'supervisor', label: 'Supervisor' },
  { id: 'requirements', label: 'Requirements & Design' },
  { id: 'code', label: 'Code & Refactoring' },
  { id: 'testing', label: 'QA & Testing' },
  { id: 'devops', label: 'DevOps & Monitoring' }
]

const activeTab = ref<TabKey>('supervisor')
const composerInput = ref<string>('')
const isSending = ref<boolean>(false)
const messagesContainer = ref<HTMLElement | null>(null)

// Advisory message types for Step 4
interface ProposedChange {
  title: string
  reason: string
  status: 'pending' | 'approved'
}

interface DisplayChatMessage {
  id: string
  tabId: TabKey
  senderType: 'user' | 'specialist' | 'proposal' | 'synthesizer'
  senderName: string
  avatarInitial?: string
  roleBadge?: string
  text?: string
  timestamp: string
  proposal?: ProposedChange
}

const chatMessages = ref<DisplayChatMessage[]>([
  // Supervisor tab thread matching design image
  {
    id: 'msg-sup-1',
    tabId: 'supervisor',
    senderType: 'user',
    senderName: 'Team representative',
    avatarInitial: 'TL',
    roleBadge: 'Question',
    text: 'Can we keep the release checklist recommendation, but make it the next priority after the CI test gate? We want to automate build checks first, then make the release runbook repeatable.',
    timestamp: '09:43'
  },
  {
    id: 'msg-sup-2',
    tabId: 'supervisor',
    senderType: 'proposal',
    senderName: 'Synthesizer',
    timestamp: '09:44',
    proposal: {
      title:
        'Swap Deployment priority from High to Medium. Keep the recommendation, but move it below the CI test gate so the team automates build checks before refining the release runbook.',
      reason:
        'The team wants to verify the CI test gate before making the release checklist repeatable. This keeps the recommendation, but changes the order of delivery.',
      status: 'pending'
    }
  },
  {
    id: 'msg-sup-3',
    tabId: 'supervisor',
    senderType: 'synthesizer',
    senderName: 'Synthesizer',
    avatarInitial: 'Y',
    roleBadge: 'Report note',
    text: 'If approved, this change will update the Deployment recommendation and the report summary. The PDF export will reflect the selected version, not the pending proposal.',
    timestamp: '09:45'
  },

  // Requirements tab thread
  {
    id: 'msg-req-1',
    tabId: 'requirements',
    senderType: 'specialist',
    senderName: 'Requirements & Design',
    avatarInitial: 'R',
    roleBadge: 'Specialist note',
    text: 'Acceptance criteria documentation was confirmed as variable in Jira. The recommendation prioritises Definition of Ready checkpoints before sprint commitment.',
    timestamp: '09:42'
  },
  {
    id: 'msg-req-2',
    tabId: 'requirements',
    senderType: 'user',
    senderName: 'Team representative',
    avatarInitial: 'TL',
    roleBadge: 'Response',
    text: 'Agreed. Having a clear checklist will stop ambiguous tickets entering sprint backlog.',
    timestamp: '09:43'
  },

  // Code & Refactoring tab thread
  {
    id: 'msg-code-1',
    tabId: 'code',
    senderType: 'specialist',
    senderName: 'Code & Refactoring',
    avatarInitial: 'C',
    roleBadge: 'Specialist note',
    text: 'Identified opportunities for Copilot piloting in repetitive FastAPI endpoint boilerplate. Peer review remains mandatory.',
    timestamp: '09:44'
  },
  {
    id: 'msg-code-2',
    tabId: 'code',
    senderType: 'user',
    senderName: 'Team representative',
    avatarInitial: 'TL',
    roleBadge: 'Response',
    text: 'We plan to trial this in sprint 14 with two senior pair programmers.',
    timestamp: '09:45'
  },

  // QA & Testing tab thread
  {
    id: 'msg-qa-1',
    tabId: 'testing',
    senderType: 'specialist',
    senderName: 'QA & Testing',
    avatarInitial: 'Q',
    roleBadge: 'Specialist note',
    text: 'Test files proxy sits at 14.3%. Adding automated pytest and Vitest runs to the pipeline will provide a reliable baseline before AI test generation.',
    timestamp: '09:45'
  },

  // DevOps & Monitoring tab thread
  {
    id: 'msg-dev-1',
    tabId: 'devops',
    senderType: 'specialist',
    senderName: 'DevOps & Monitoring',
    avatarInitial: 'D',
    roleBadge: 'Specialist note',
    text: 'Repository has Dockerfile and build.yml without detected deploy step. Turning the manual checklist into a repeatable delivery gate is recommended.',
    timestamp: '09:46'
  }
])

const currentTabMessages = computed(() => {
  return chatMessages.value.filter((m) => m.tabId === activeTab.value)
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function selectTab(tabKey: TabKey) {
  activeTab.value = tabKey
  scrollToBottom()
}

// Composer & Send logic
async function handleSendMessage() {
  const content = composerInput.value.trim()
  if (!content || isSending.value) return

  composerInput.value = ''
  isSending.value = true

  const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  // Optimistic push
  chatMessages.value.push({
    id: `msg-user-${Date.now()}`,
    tabId: activeTab.value,
    senderType: 'user',
    senderName: 'Team representative',
    avatarInitial: 'TL',
    roleBadge: 'Question',
    text: content,
    timestamp: now
  })
  scrollToBottom()

  try {
    if (!api.USE_MOCKS && store.sessionId) {
      const res = await api.backendClient.sendAdvisorMessage(store.sessionId, content)
      const reply = res.messages.find((m) => m.role !== 'user')
      if (reply) {
        chatMessages.value.push({
          id: reply.id,
          tabId: activeTab.value,
          senderType: 'specialist',
          senderName: reply.agent_label || 'Specialist',
          avatarInitial: (reply.agent_label || 'S').charAt(0).toUpperCase(),
          roleBadge: 'Response',
          text: reply.content,
          timestamp: reply.timestamp
            ? new Date(reply.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : now
        })
      }
    } else {
      const reply = await api.sendAdvisorMessage(content)
      chatMessages.value.push({
        id: reply.id,
        tabId: activeTab.value,
        senderType: 'specialist',
        senderName: reply.senderName || 'Synthesizer',
        avatarInitial: 'Y',
        roleBadge: reply.role || 'Response',
        text: reply.content,
        timestamp: reply.timestamp || now
      })
    }
    scrollToBottom()
  } catch (err) {
    console.warn('Failed to send advisory message:', err)
  } finally {
    isSending.value = false
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendMessage()
  }
}

// Report Lifecycle
onMounted(async () => {
  store.ensureSampleSignals()
  store.setStep(4)

  if (!isMock.value && store.sessionId) {
    if (!store.diagnostic) {
      try {
        store.diagnostic = await api.getExistingDiagnostic(store.sessionId)
      } catch (err) {
        console.warn('No report available yet for this session:', err)
        reportNotReady.value = true
      }
    }
    return
  }

  if (!store.diagnostic) {
    store.diagnostic = JSON.parse(JSON.stringify(mockDiagnosticReport))
  }

  scrollToBottom()
})

const report = computed<DiagnosticReport>(() => {
  return store.diagnostic || mockDiagnosticReport
})

// Right Column: Atlas Service Context Card Info
const contextSubtitle = computed(() => {
  if (isMock.value) {
    return '48 code files · FastAPI + React · 6 test files / 42 source files'
  }
  const signals = store.repoSignals
  if (signals) {
    const fw = signals.stack.frameworks.slice(0, 2).join(' + ') || 'Analyzed'
    return `${signals.totalSupportedFiles} code files · ${fw} · ${signals.quality.testFilesCount} test files / ${signals.quality.sourceFilesCount} source files`
  }
  return report.value.projectProfile.codeFilesSummary || 'Repository evidence analyzed'
})

const contextKeyValues = computed(() => [
  {
    key: 'Repository',
    value: isMock.value
      ? 'Reviewed · 6 signal groups'
      : (store.repoSignals ? 'Reviewed · Signal groups active' : 'Reviewed · 6 signal groups')
  },
  {
    key: 'Scope',
    value: isMock.value
      ? '48 code files · PoC eligible'
      : `${store.repoSignals?.totalSupportedFiles || 48} code files · ${store.repoSignals?.isEligiblePoC ? 'PoC eligible' : 'Under review'}`
  },
  {
    key: 'Team',
    value: isMock.value ? 'Scrum · 8 members' : (store.answers['methodology']?.answerText || 'Scrum · 8 members')
  },
  {
    key: 'AI starting point',
    value: isMock.value ? 'Exploratory' : (store.answers['ai-maturity']?.answerText || 'Exploratory')
  },
  {
    key: 'Pain points',
    value: isMock.value ? '7 selected' : (store.answers['pain-points']?.answerText ? 'Declared' : '7 selected')
  },
  {
    key: 'Current tools',
    value: isMock.value ? 'Copilot pilot · ChatGPT' : (store.answers['tools-used']?.answerText || 'Copilot pilot · ChatGPT')
  }
])

// Section 4: Accordion Rows (Requirements, Testing, Deployment, Design, Development, Monitoring)
export interface AccordionRecItem {
  id: string
  phaseKey: string
  phaseName: string
  priority: RecommendationPriority
  title: string
  quickWin?: boolean
  actionText?: string
  repositoryEvidence?: string
  teamInput?: string
  justification?: string
  examplePractice?: string
  expectedImpact?: string
  effort?: string
}

const openRecommendationIndex = ref<number | null>(null)

function toggleRecommendation(idx: number) {
  openRecommendationIndex.value = openRecommendationIndex.value === idx ? null : idx
}

const accordionRecommendations = computed<AccordionRecItem[]>(() => {
  const desiredOrder = [
    { key: 'requirements', name: 'Requirements', defaultPriority: 'high' as RecommendationPriority, defaultQuickWin: true },
    { key: 'testing', name: 'Testing', defaultPriority: 'high' as RecommendationPriority, defaultQuickWin: false },
    { key: 'deployment', name: 'Deployment', defaultPriority: 'high' as RecommendationPriority, defaultQuickWin: false },
    { key: 'design', name: 'Design', defaultPriority: 'medium' as RecommendationPriority, defaultQuickWin: true },
    { key: 'development', name: 'Development', defaultPriority: 'medium' as RecommendationPriority, defaultQuickWin: false },
    { key: 'monitoring', name: 'Monitoring', defaultPriority: 'low' as RecommendationPriority, defaultQuickWin: false }
  ]

  return desiredOrder.map((spec) => {
    // 1. Try finding in report.phases with exact key or backend composite key
    let foundRec: any = null
    const sec = report.value.phases[spec.key]
    if (sec && sec.recommendations && sec.recommendations.length > 0) {
      foundRec = sec.recommendations[0]
    } else {
      // Check composite keys in backend mode
      if (spec.key === 'requirements' && report.value.phases['requirements_design']?.recommendations?.[0]) {
        foundRec = report.value.phases['requirements_design'].recommendations[0]
      } else if (spec.key === 'design' && report.value.phases['requirements_design']?.recommendations?.[1]) {
        foundRec = report.value.phases['requirements_design'].recommendations[1]
      } else if (spec.key === 'development' && report.value.phases['code_refactoring']?.recommendations?.[0]) {
        foundRec = report.value.phases['code_refactoring'].recommendations[0]
      } else if (spec.key === 'testing' && report.value.phases['qa_testing']?.recommendations?.[0]) {
        foundRec = report.value.phases['qa_testing'].recommendations[0]
      } else if (spec.key === 'deployment' && report.value.phases['devops_monitoring']?.recommendations?.[0]) {
        foundRec = report.value.phases['devops_monitoring'].recommendations[0]
      } else if (spec.key === 'monitoring' && report.value.phases['devops_monitoring']?.recommendations?.[1]) {
        foundRec = report.value.phases['devops_monitoring'].recommendations[1]
      }
    }

    // Default mock data copy for each phase
    const mockPhaseSec = mockDiagnosticReport.phases[spec.key]
    const mockRec = mockPhaseSec?.recommendations?.[0]

    return {
      id: foundRec?.id || mockRec?.id || `rec-${spec.key}`,
      phaseKey: spec.key,
      phaseName: spec.name,
      priority: foundRec?.priority || mockRec?.priority || spec.defaultPriority,
      title: foundRec?.title || mockRec?.title || `Establish ${spec.name} practices`,
      quickWin: foundRec?.quickWin ?? mockRec?.quickWin ?? spec.defaultQuickWin,
      actionText: foundRec?.actionText || mockRec?.actionText || foundRec?.justification || mockRec?.justification,
      repositoryEvidence: foundRec?.repositoryEvidence || mockRec?.repositoryEvidence,
      teamInput: foundRec?.teamInput || mockRec?.teamInput,
      justification: foundRec?.justification || mockRec?.justification,
      examplePractice: foundRec?.examplePractice || mockRec?.examplePractice,
      expectedImpact: foundRec?.expectedImpact || mockRec?.expectedImpact,
      effort: foundRec?.effort || mockRec?.effort
    }
  })
})

function getPriorityBadgeClass(priority: string): string {
  switch (priority.toLowerCase()) {
    case 'high':
      return 'badge-purple'
    case 'medium':
      return 'badge-info'
    case 'low':
      return 'badge-poc'
    default:
      return 'badge-poc'
  }
}

// Section 5: "About this report" Accordion
const isAboutReportOpen = ref<boolean>(false)

function toggleAboutReport() {
  isAboutReportOpen.value = !isAboutReportOpen.value
}

// Export PDF
async function handleExportPdf() {
  isExporting.value = true
  exportNotice.value = ''
  try {
    const res = await api.exportPdfReport(store.sessionId || undefined)
    exportNotice.value = res.isPdf
      ? `Report successfully downloaded as PDF: ${res.filename}`
      : `Report downloaded as HTML deliverable: ${res.filename} (PDF renderer not available on host)`
    setTimeout(() => {
      exportNotice.value = ''
    }, 6000)
  } catch (err: unknown) {
    const anyErr = err as { message?: string }
    exportNotice.value = anyErr.message || 'Report download failed. Please retry.'
  } finally {
    isExporting.value = false
  }
}

function goBackToQuestions() {
  store.setStep(3)
  router.push('/questions')
}
</script>

<template>
  <div v-if="reportNotReady" class="report-view container not-ready-state">
    <div class="screen-meta">
      <span class="step-badge">TEAM DIAGNOSTIC / STEP 4 OF 4</span>
      <h1 class="page-title">Report isn't ready yet</h1>
      <p class="page-subtitle">
        The diagnostic conversation hasn't finished — one or more specialists are still working or
        waiting on an answer. Head back to Team context to continue it.
      </p>
    </div>
    <button type="button" class="btn-primary" @click="goBackToQuestions">
      Back to team context
    </button>
  </div>

  <div v-else-if="report" class="report-view container">
    <!-- Top Sample Data Banner -->
    <div v-if="isMock" class="sample-data-banner">
      <span class="sample-tag">Sample data</span>
      Illustrative project, repository signals, team inputs and recommendations. Static preview only.
    </div>

    <!-- 1. Header Row -->
    <header class="report-header-row">
      <div class="screen-meta">
        <span class="step-badge">TEAM DIAGNOSTIC / STEP 4 OF 4</span>
        <h1 class="page-title">{{ report.repoName }} diagnostic workspace</h1>
        <p class="page-subtitle">
          The diagnostic is not final. Keep the conversation open, question the project, edit the report and export a static PDF snapshot of the selected version.
        </p>
      </div>

      <div class="header-specialists-block">
        <span class="badge badge-purple">4 active specialists</span>
        <p class="header-specialists-sub">
          Supervisor coordinates the advisory chat · Synthesizer prioritises the report
        </p>
      </div>
    </header>

    <!-- Export Toast Notice -->
    <div v-if="exportNotice" class="export-toast card" role="status" aria-live="polite">
      <svg class="toast-check-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
        <path
          fill-rule="evenodd"
          d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
          clip-rule="evenodd"
        />
      </svg>
      <span>{{ exportNotice }}</span>
    </div>

    <!-- 2. Two Columns Layout -->
    <div class="workspace-two-col-grid">
      <!-- Left Column: Advisory Chat Card -->
      <section class="advisory-chat-card card" aria-label="Advisory chat">
        <div class="chat-card-header">
          <div>
            <h2 class="chat-title">Advisory chat</h2>
            <p class="chat-subtitle">Supervisor coordinates questions from Requirements, Code, QA and DevOps.</p>
          </div>
          <span class="badge badge-purple">4 active specialists</span>
        </div>

        <!-- Specialist Navigation Tabs -->
        <div class="chat-tabs-bar" role="tablist" aria-label="Advisory chat tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.id"
            class="chat-tab-btn"
            :class="{ 'tab-active': activeTab === tab.id }"
            @click="selectTab(tab.id)"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Messages Stream (Fixed height 380px, internal scroll, anchored to bottom) -->
        <div
          ref="messagesContainer"
          class="messages-stream"
          aria-label="Conversation messages"
        >
          <div class="messages-inner-anchor">
            <template v-for="msg in currentTabMessages" :key="msg.id">
              <!-- Case A: Proposed Change Card -->
              <div v-if="msg.senderType === 'proposal' && msg.proposal" class="proposal-card-block">
                <div class="proposal-card-header">
                  <span class="proposal-label">Proposed change</span>
                  <span class="badge badge-warning">Pending approval</span>
                </div>
                <h4 class="proposal-title">{{ msg.proposal.title }}</h4>
                <p class="proposal-reason">
                  <strong>Reason:</strong> {{ msg.proposal.reason }}
                </p>
              </div>

              <!-- Case B: Synthesizer Report Note -->
              <div v-else-if="msg.senderType === 'synthesizer'" class="message-row message-synthesizer">
                <div class="avatar avatar-synthesizer" aria-hidden="true">
                  <span>{{ msg.avatarInitial || 'Y' }}</span>
                </div>
                <div class="bubble-container">
                  <div class="bubble-header">
                    <span class="sender-name">{{ msg.senderName }}</span>
                    <span class="meta-subtitle">{{ msg.timestamp }} · {{ msg.roleBadge || 'Report note' }}</span>
                  </div>
                  <div class="bubble-body synth-bubble-body">
                    <p class="bubble-text">{{ msg.text }}</p>
                  </div>
                </div>
              </div>

              <!-- Case C: User message -->
              <div v-else-if="msg.senderType === 'user'" class="message-row message-user">
                <div class="avatar avatar-user" aria-hidden="true">
                  <span>{{ msg.avatarInitial || 'TL' }}</span>
                </div>
                <div class="bubble-container">
                  <div class="bubble-header">
                    <span class="sender-name">{{ msg.senderName }}</span>
                    <span class="meta-subtitle">{{ msg.timestamp }} · {{ msg.roleBadge || 'Question' }}</span>
                  </div>
                  <div class="bubble-body user-bubble-body">
                    <p class="bubble-text">{{ msg.text }}</p>
                  </div>
                </div>
              </div>

              <!-- Case D: Regular Specialist Message -->
              <div v-else class="message-row message-specialist">
                <div class="avatar avatar-specialist" aria-hidden="true">
                  <span>{{ msg.avatarInitial || 'S' }}</span>
                </div>
                <div class="bubble-container">
                  <div class="bubble-header">
                    <span class="sender-name">{{ msg.senderName }}</span>
                    <span class="meta-subtitle">{{ msg.timestamp }} · {{ msg.roleBadge || 'Specialist' }}</span>
                  </div>
                  <div class="bubble-body specialist-bubble-body">
                    <p class="bubble-text">{{ msg.text }}</p>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- Composer Area -->
        <div class="chat-composer-section">
          <div class="composer-header-row">
            <span class="composer-title">Message composer</span>
            <span class="draft-indicator">Draft saved automatically</span>
          </div>

          <div class="composer-input-row">
            <textarea
              v-model="composerInput"
              rows="2"
              class="composer-textarea"
              placeholder="Ask a follow-up question, challenge a recommendation or edit a report section"
              :disabled="isSending"
              aria-label="Ask a follow-up question, challenge a recommendation or edit a report section"
              @keydown="handleKeyDown"
            ></textarea>
            <button
              type="button"
              class="btn-primary composer-send-btn"
              :disabled="isSending || !composerInput.trim()"
              @click="handleSendMessage"
            >
              Send
            </button>
          </div>

          <div class="composer-helper-row">
            <span class="footnote-text">
              <template v-if="isMock">Sample data · </template>Keep it concise. Do not include personal data, client identifiers, secrets or sensitive source code. Remove sensitive details before submitting.
            </span>
          </div>
        </div>
      </section>

      <!-- Right Column: Context card + Executive summary card -->
      <aside class="right-panel-column" aria-label="Context & Executive summary">
        <!-- (a) Atlas Service Context Card -->
        <div class="card context-card">
          <div class="context-card-header">
            <h3 class="context-title">{{ report.repoName }}</h3>
            <p class="context-sub">
              <template v-if="isMock">Sample data · </template>{{ contextSubtitle }}
            </p>
          </div>

          <div class="context-attributes-table">
            <div v-for="item in contextKeyValues" :key="item.key" class="context-attr-row">
              <span class="context-attr-key">{{ item.key }}</span>
              <span class="context-attr-val">{{ item.value }}</span>
            </div>
          </div>
        </div>

        <!-- (b) Executive Summary Lavender Card -->
        <div class="card executive-summary-card">
          <div class="exec-eyebrow">
            EXECUTIVE SUMMARY<template v-if="isMock"> / SAMPLE DATA</template>
          </div>
          <h3 class="exec-headline">{{ report.headline }}</h3>
          <p class="exec-paragraph">{{ report.executiveSummary }}</p>

          <!-- Recommended starting point stat box -->
          <div class="recommended-start-box">
            <span class="rec-start-title">RECOMMENDED STARTING POINT</span>
            <div class="rec-stats-list">
              <div class="rec-stat-item">
                <span class="rec-stat-number">{{ report.metrics?.highPriorityCount ?? 3 }}</span>
                <span class="rec-stat-label">High-priority phases</span>
              </div>
              <div class="rec-stat-item">
                <span class="rec-stat-number stat-green">{{ report.metrics?.quickWinsCount ?? 2 }}</span>
                <span class="rec-stat-label">Quick wins to pilot</span>
              </div>
              <div class="rec-stat-item">
                <span class="rec-stat-number">{{ report.metrics?.phasesCoveredCount ?? 6 }}</span>
                <span class="rec-stat-label">SDLC phases covered</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- 3. Full-width Amber Banner -->
    <div class="card evidence-gap-banner" role="region" aria-label="Evidence gaps alert">
      <div class="banner-icon-circle" aria-hidden="true">
        <svg viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
            clip-rule="evenodd"
          />
        </svg>
      </div>
      <div class="banner-text-block">
        <strong class="banner-headline">
          {{ report.evidenceGapAlert?.title || 'Resolve evidence gaps before acting' }}
        </strong>
        <p class="banner-body">
          {{ report.evidenceGapAlert?.description || 'The team expects CI tests, but build.yml contains no detected test job. Monitoring is self-declared as external, while repository telemetry signals are missing. Validate both boundaries; absence of evidence is not evidence of absence.' }}
        </p>
      </div>
    </div>

    <!-- 4. Recommendations by Priority Accordion -->
    <section class="recommendations-section" aria-label="Recommendations by priority">
      <div class="recommendations-header-row">
        <div>
          <h2 class="recommendations-title">Recommendations by priority</h2>
          <p class="recommendations-sub">
            <template v-if="isMock">Sample data · </template>Qualitative expected impacts, not guaranteed outcomes. Tool examples are illustrative.
          </p>
        </div>
        <span class="badge badge-poc">Human review required</span>
      </div>

      <!-- 6 Accordion Rows -->
      <div class="accordion-list">
        <div
          v-for="(rec, index) in accordionRecommendations"
          :key="rec.id"
          class="accordion-item card"
          :class="{ 'accordion-open': openRecommendationIndex === index }"
        >
          <!-- Real Accessible Button Header -->
          <button
            type="button"
            class="accordion-header-btn"
            :aria-expanded="openRecommendationIndex === index"
            :aria-controls="`accordion-body-${rec.phaseKey}`"
            :id="`accordion-header-${rec.phaseKey}`"
            @click="toggleRecommendation(index)"
          >
            <div class="header-left-group">
              <span class="row-phase-name">{{ rec.phaseName }}</span>
              <span class="badge" :class="getPriorityBadgeClass(rec.priority)">
                {{ rec.priority }} priority
              </span>
              <span class="row-title">{{ rec.title }}</span>
            </div>

            <div class="header-right-group">
              <span v-if="rec.quickWin" class="badge badge-success">Quick win</span>
              <svg
                class="chevron-icon"
                :class="{ 'chevron-rotated': openRecommendationIndex === index }"
                viewBox="0 0 16 16"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fill-rule="evenodd"
                  d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06l-3.25 3.25a.75.75 0 0 1-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 0 1 0-1.06Z"
                  clip-rule="evenodd"
                />
              </svg>
            </div>
          </button>

          <!-- Expanded Body Content -->
          <div
            v-if="openRecommendationIndex === index"
            :id="`accordion-body-${rec.phaseKey}`"
            role="region"
            :aria-labelledby="`accordion-header-${rec.phaseKey}`"
            class="accordion-body"
          >
            <!-- Recommended action text -->
            <div v-if="rec.actionText" class="rec-action-box">
              <p class="rec-action-text">{{ rec.actionText }}</p>
            </div>

            <!-- Two-column inner block: Why this recommendation & Example practice -->
            <div class="rec-details-grid">
              <!-- Left: Why this recommendation -->
              <div v-if="rec.repositoryEvidence || rec.teamInput || rec.justification" class="rec-why-card">
                <span class="block-label">WHY THIS RECOMMENDATION</span>
                <p v-if="rec.repositoryEvidence" class="evidence-line">
                  <strong class="sub-label">Repository evidence:</strong> {{ rec.repositoryEvidence }}
                </p>
                <p v-if="rec.teamInput" class="team-input-line">
                  <strong class="sub-label">Team input:</strong> {{ rec.teamInput }}
                </p>
                <p v-else-if="!rec.repositoryEvidence && rec.justification" class="justification-fallback">
                  {{ rec.justification }}
                </p>
              </div>

              <!-- Right: Example Practice -->
              <div v-if="rec.examplePractice" class="rec-practice-card">
                <span class="block-label">EXAMPLE PRACTICE</span>
                <p class="practice-text">{{ rec.examplePractice }}</p>
              </div>
            </div>

            <!-- Impact and Effort Row -->
            <div v-if="rec.expectedImpact || rec.effort" class="rec-metrics-bar">
              <div v-if="rec.expectedImpact" class="metric-cell">
                <span class="metric-key">EXPECTED IMPACT</span>
                <span class="metric-value">{{ rec.expectedImpact }}</span>
              </div>
              <div v-if="rec.effort" class="metric-cell">
                <span class="metric-key">ADOPTION EFFORT</span>
                <span class="metric-value">{{ rec.effort }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 5. "About this report" Accordion Row (Closed by default) -->
    <div class="about-report-section card" :class="{ 'accordion-open': isAboutReportOpen }">
      <button
        type="button"
        class="about-report-btn"
        :aria-expanded="isAboutReportOpen"
        aria-controls="about-report-body"
        id="about-report-header"
        @click="toggleAboutReport"
      >
        <div class="about-btn-left">
          <span class="about-title">About this report</span>
          <span class="about-sub">Scope, limitations &amp; PDF details</span>
        </div>
        <svg
          class="chevron-icon"
          :class="{ 'chevron-rotated': isAboutReportOpen }"
          viewBox="0 0 16 16"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fill-rule="evenodd"
            d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06l-3.25 3.25a.75.75 0 0 1-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 0 1 0-1.06Z"
            clip-rule="evenodd"
          />
        </svg>
      </button>

      <!-- About this report expanded body -->
      <div
        v-if="isAboutReportOpen"
        id="about-report-body"
        role="region"
        aria-labelledby="about-report-header"
        class="about-report-body"
      >
        <div class="about-two-col-grid">
          <!-- Left: Scope, limitations and next horizon -->
          <div class="about-left-col">
            <h3 class="about-section-heading">Scope, limitations and next horizon</h3>

            <div class="about-subgroup">
              <span class="badge badge-poc">CURRENT POC SCOPE</span>
              <ul class="about-bullet-list">
                <li
                  v-for="(item, idx) in report.scopeAndLimitations?.currentPocScope || []"
                  :key="idx"
                  class="about-bullet-item"
                >
                  <span class="bullet-dot" aria-hidden="true">•</span>
                  <span>{{ item }}</span>
                </li>
              </ul>
            </div>

            <div class="about-subgroup">
              <span class="block-label-bold">Data handling</span>
              <p class="about-text-line">
                Code is temporarily processed and deleted after scanning. Extracted signals are shared with the AI service; code excerpts require approval. Full source code is not shared.
              </p>
            </div>

            <div class="about-subgroup">
              <span class="block-label-bold">Enterprise roadmap · Future scope, not available today</span>
              <ul class="about-bullet-list">
                <li
                  v-for="(item, idx) in report.scopeAndLimitations?.enterpriseRoadmap || []"
                  :key="idx"
                  class="about-bullet-item"
                >
                  <span class="bullet-dot" aria-hidden="true">•</span>
                  <span>{{ item }}</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- Right: Review-Ready PDF Structure Preview -->
          <div class="about-right-col">
            <h3 class="about-section-heading">A review-ready PDF structure</h3>
            <p class="about-sub-desc">
              Designed output for stakeholder review, carrying sample data and report version.
            </p>

            <ul class="pdf-checklist">
              <li class="pdf-check-item">
                <span class="check-pill" aria-hidden="true">✓</span>
                <span>Cover &amp; report metadata</span>
              </li>
              <li class="pdf-check-item">
                <span class="check-pill" aria-hidden="true">✓</span>
                <span>Executive summary</span>
              </li>
              <li class="pdf-check-item">
                <span class="check-pill" aria-hidden="true">✓</span>
                <span>Repository &amp; team context profile</span>
              </li>
              <li class="pdf-check-item">
                <span class="check-pill" aria-hidden="true">✓</span>
                <span>All six phase recommendations</span>
              </li>
              <li class="pdf-check-item">
                <span class="check-pill" aria-hidden="true">✓</span>
                <span>Evidence scope &amp; limitations</span>
              </li>
            </ul>

            <p class="pdf-footnote">
              Export PDF is a static snapshot of the selected version.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- 6. Footer Navigation & Export Row -->
    <footer class="report-footer-bar">
      <button type="button" class="btn-secondary back-step-btn" @click="goBackToQuestions">
        <svg class="nav-arrow" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M9.78 3.22a.75.75 0 0 1 0 1.06L6.06 8l3.72 3.72a.75.75 0 1 1-1.06 1.06L4.47 8.53a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z"
            clip-rule="evenodd"
          />
        </svg>
        <span>Back to team context</span>
      </button>

      <div class="footer-right-actions">
        <span class="footer-guidance-note">
          Use the diagnostic to guide a team discussion, not replace delivery judgement.
        </span>

        <button
          type="button"
          class="btn-primary export-action-btn"
          :disabled="isExporting"
          @click="handleExportPdf"
        >
          <svg class="action-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path
              d="M3.5 2a.5.5 0 0 0-.5.5v11a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5V7.707a.5.5 0 0 0-.146-.354l-4.708-4.707A.5.5 0 0 0 8.293 2.5H3.5Zm5 1.5v3.5a.5.5 0 0 0 .5.5H12l-3.5-4Z"
            />
          </svg>
          <span>{{ isExporting ? 'Exporting...' : 'Export PDF' }}</span>
        </button>
      </div>
    </footer>

    <!-- Bottom Disclaimer Row -->
    <div class="bottom-disclaimer-row">
      <span>Independent concept · Not affiliated with or endorsed by Accenture</span>
      <span>Static preview · Human review required</span>
    </div>
  </div>
</template>

<style scoped>
.report-view {
  padding-top: 1.5rem;
  padding-bottom: 4rem;
}

/* Sample Data Banner */
.sample-data-banner {
  background-color: var(--color-primary-light);
  border: 1px solid var(--color-primary-border);
  color: var(--color-primary);
  border-radius: var(--radius-md);
  padding: 0.625rem 1rem;
  font-size: 0.8125rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-bottom: 1.5rem;
}

.sample-tag {
  background-color: var(--color-primary);
  color: var(--color-text-inverted);
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* 1. Header Row */
.report-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.screen-meta {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  max-width: 680px;
}

.step-badge {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-primary);
}

.page-title {
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--color-text-primary);
  line-height: 1.25;
}

.page-subtitle {
  font-size: 0.9375rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.header-specialists-block {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.375rem;
  text-align: right;
  max-width: 380px;
}

.header-specialists-sub {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.35;
}

/* Export Toast */
.export-toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  z-index: 100;
  background-color: #0f172a;
  color: #ffffff;
  padding: 0.875rem 1.25rem;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid #334155;
  animation: slideUp 0.25s ease-out;
}

.toast-check-icon {
  width: 18px;
  height: 18px;
  color: #4ade80;
}

@keyframes slideUp {
  from {
    transform: translateY(16px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* 2. Two Columns Layout */
.workspace-two-col-grid {
  display: grid;
  grid-template-columns: 1.45fr 1fr;
  gap: 1.75rem;
  align-items: stretch;
  margin-bottom: 2rem;
}

/* Left Column: Advisory Chat Card */
.advisory-chat-card {
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: 100%;
}

.chat-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.chat-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.3;
}

.chat-subtitle {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
  margin-top: 0.125rem;
}

/* Specialist Tabs */
.chat-tabs-bar {
  display: flex;
  gap: 0.375rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.5rem;
  overflow-x: auto;
  scrollbar-width: none;
}

.chat-tabs-bar::-webkit-scrollbar {
  display: none;
}

.chat-tab-btn {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  background-color: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  min-height: 32px;
}

.chat-tab-btn:hover {
  color: var(--color-primary);
  background-color: var(--color-primary-light);
}

.chat-tab-btn.tab-active {
  background-color: var(--color-primary);
  color: var(--color-text-inverted);
}

/* Messages Stream */
.messages-stream {
  flex: 1;
  min-height: 500px;
  overflow-y: auto;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: 1rem;
  background-color: #fafbfd;
  display: flex;
  flex-direction: column;
}

.messages-inner-anchor {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Messages generic */
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  animation: fadeIn 0.15s ease-out;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
}

.avatar-user {
  background-color: var(--color-primary);
  color: #ffffff;
}

.avatar-specialist {
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  border: 1px solid var(--color-primary-border);
}

.avatar-synthesizer {
  background-color: #ede9fe;
  color: #6d3cc8;
  border: 1px solid #ddd6fe;
}

.bubble-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.bubble-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  padding-left: 0.25rem;
}

.sender-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.meta-subtitle {
  color: var(--color-text-muted);
}

.bubble-body {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-lg);
  font-size: 0.875rem;
  line-height: 1.5;
  box-shadow: var(--shadow-sm);
}

.user-bubble-body {
  background-color: #faf5ff;
  border: 1.5px solid #c084fc;
}

.specialist-bubble-body {
  background-color: #ffffff;
  border: 1px solid var(--color-border);
}

.synth-bubble-body {
  background-color: #fdfcff;
  border: 1px solid #e2e8f0;
}

.bubble-text {
  color: var(--color-text-primary);
  white-space: pre-line;
}

/* Proposed change card */
.proposal-card-block {
  background-color: #fffbeb;
  border: 1.5px solid #fde68a;
  border-radius: var(--radius-md);
  padding: 0.875rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  box-shadow: var(--shadow-sm);
}

.proposal-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.proposal-label {
  font-size: 0.8125rem;
  font-weight: 700;
  color: #92400e;
}

.proposal-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.45;
}

.proposal-reason {
  font-size: 0.8125rem;
  color: #92400e;
  line-height: 1.4;
}

/* Composer Section */
.chat-composer-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.25rem;
}

.composer-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.composer-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.draft-indicator {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.composer-input-row {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
}

.composer-textarea {
  flex: 1;
  font-family: inherit;
  font-size: 0.875rem;
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-surface);
  color: var(--color-text-primary);
  resize: vertical;
  min-height: 48px;
  max-height: 120px;
  line-height: 1.45;
}

.composer-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.composer-send-btn {
  min-height: 42px;
  padding: 0.5rem 1.25rem;
  font-weight: 600;
  align-self: stretch;
}

.composer-helper-row {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  line-height: 1.4;
}

/* Right Column Panels */
.right-panel-column {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Context Card */
.context-card {
  padding: 1.25rem 1.5rem;
}

.context-card-header {
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: 0.75rem;
  margin-bottom: 0.75rem;
}

.context-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.context-sub {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.125rem;
}

.context-attributes-table {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.context-attr-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8125rem;
  padding: 0.125rem 0;
}

.context-attr-key {
  color: var(--color-text-muted);
  font-weight: 500;
}

.context-attr-val {
  color: var(--color-text-primary);
  font-weight: 600;
  text-align: right;
}

/* Executive Summary Lavender Card */
.executive-summary-card {
  background-color: #f5f3ff;
  border: 1.5px solid #c084fc;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.exec-eyebrow {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--color-primary);
  text-transform: uppercase;
}

.exec-headline {
  font-size: 1.4rem;
  font-weight: 700;
  color: #1e1b4b;
  line-height: 1.3;
  letter-spacing: -0.01em;
}

.exec-paragraph {
  font-size: 0.875rem;
  color: #475569;
  line-height: 1.55;
}

.recommended-start-box {
  background-color: #ede9fe;
  border: 1px solid #ddd6fe;
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 0.25rem;
}

.rec-start-title {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--color-primary);
}

.rec-stats-list {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.rec-stat-item {
  display: flex;
  align-items: baseline;
  gap: 0.625rem;
}

.rec-stat-number {
  font-size: 1.5rem;
  font-weight: 800;
  line-height: 1;
  color: #4338ca;
  min-width: 20px;
}

.rec-stat-number.stat-green {
  color: #15803d;
}

.rec-stat-label {
  font-size: 0.8125rem;
  color: #334155;
  font-weight: 500;
}

/* 3. Evidence Gap Amber Banner */
.evidence-gap-banner {
  background-color: #fffbeb;
  border: 1.5px solid #fde68a;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 2rem;
}

.banner-icon-circle {
  width: 24px;
  height: 24px;
  color: #d97706;
  flex-shrink: 0;
  margin-top: 2px;
}

.banner-icon-circle svg {
  width: 100%;
  height: 100%;
}

.banner-text-block {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.banner-headline {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #92400e;
}

.banner-body {
  font-size: 0.875rem;
  color: #92400e;
  line-height: 1.5;
}

/* 4. Recommendations Accordion Section */
.recommendations-section {
  margin-bottom: 2rem;
}

.recommendations-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.recommendations-title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.recommendations-sub {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  margin-top: 0.125rem;
}

.accordion-list {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.accordion-item {
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.accordion-item:hover {
  border-color: var(--color-border-strong);
}

.accordion-item.accordion-open {
  border-color: #c084fc;
  box-shadow: var(--shadow-sm);
}

.accordion-header-btn {
  width: 100%;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  background-color: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.header-left-group {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  flex: 1;
  min-width: 0;
}

.row-phase-name {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-text-primary);
  min-width: 110px;
}

.row-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-right-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.chevron-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-muted);
  transition: transform 0.2s ease;
}

.chevron-rotated {
  transform: rotate(90deg);
}

/* Accordion Body */
.accordion-body {
  padding: 1.25rem 1.5rem 1.5rem;
  border-top: 1px solid var(--color-border-subtle);
  background-color: #fafbfc;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  animation: fadeIn 0.15s ease-out;
}

.rec-action-box {
  font-size: 0.9375rem;
  color: var(--color-text-primary);
  line-height: 1.55;
  font-weight: 500;
}

.rec-details-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}

.rec-why-card,
.rec-practice-card {
  background-color: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1rem 1.125rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.block-label {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-primary);
}

.sub-label {
  color: var(--color-text-primary);
}

.evidence-line,
.team-input-line,
.justification-fallback {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

.practice-text {
  font-size: 0.8125rem;
  color: var(--color-text-primary);
  line-height: 1.45;
}

.rec-metrics-bar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border-subtle);
}

.metric-cell {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.metric-key {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
}

.metric-value {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

/* 5. "About this report" Accordion */
.about-report-section {
  padding: 0;
  margin-bottom: 2rem;
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.about-report-btn {
  width: 100%;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.about-btn-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.about-title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.about-sub {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.about-report-body {
  padding: 1.5rem;
  border-top: 1px solid var(--color-border-subtle);
  background-color: #fafbfc;
}

.about-two-col-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 2rem;
}

.about-left-col,
.about-right-col {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.about-section-heading {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.about-subgroup {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.block-label-bold {
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.about-bullet-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.about-bullet-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

.bullet-dot {
  color: var(--color-primary);
  font-size: 1rem;
  line-height: 1;
}

.about-text-line {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

.about-sub-desc {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.pdf-checklist {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.pdf-check-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

.check-pill {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6875rem;
  font-weight: 700;
}

.pdf-footnote {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border-subtle);
  padding-top: 0.75rem;
}

/* 6. Footer Navigation & Export Row */
.report-footer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
  margin-bottom: 2rem;
  gap: 1.5rem;
}

.back-step-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-arrow {
  width: 16px;
  height: 16px;
}

.footer-right-actions {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.footer-guidance-note {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.export-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.action-icon {
  width: 16px;
  height: 16px;
}

/* Bottom Disclaimer Row */
.bottom-disclaimer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  padding-top: 1rem;
}

/* Responsive */
@media (max-width: 1024px) {
  .workspace-two-col-grid {
    grid-template-columns: 1fr;
  }

  .rec-details-grid {
    grid-template-columns: 1fr;
  }

  .about-two-col-grid {
    grid-template-columns: 1fr;
  }

  .header-left-group {
    flex-wrap: wrap;
  }

  .row-title {
    white-space: normal;
  }

  .report-footer-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .footer-right-actions {
    flex-direction: column;
    align-items: stretch;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
