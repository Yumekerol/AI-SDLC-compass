<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import * as api from '@/api'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import TopicsProgress from '@/components/chat/TopicsProgress.vue'
import { mockAdvisorContext } from '@/mocks'
import type { SpecialistActivity, UnresolvedKnowledgeGap } from '@/types/advisor'

const router = useRouter()
const store = useSessionStore()

type TabKey = 'supervisor' | 'requirements' | 'code' | 'testing' | 'devops'

interface DisplayMessage {
  id: string
  tabId: TabKey
  sender: 'agent' | 'user'
  agentInitial?: string
  agentName: string
  roleBadge?: string
  text: string
  timestamp: string
  isSkipped?: boolean
}

const tabs = [
  { id: 'supervisor' as const, label: 'Supervisor' },
  { id: 'requirements' as const, label: 'Requirements & Design' },
  { id: 'code' as const, label: 'Code & Refactoring' },
  { id: 'testing' as const, label: 'QA & Testing' },
  { id: 'devops' as const, label: 'DevOps & Monitoring' }
]

const activeTab = ref<TabKey>('supervisor')
const composerInput = ref('')
const draftSavedMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

const isMock = computed(() => store.isMock)

// Specialists activity data (defaults to mockAdvisorContext which includes capacityPercent)
const specialists = ref<SpecialistActivity[]>(
  JSON.parse(JSON.stringify(mockAdvisorContext.specialists))
)

// Unresolved knowledge gaps data
const knowledgeGaps = ref<UnresolvedKnowledgeGap[]>(
  JSON.parse(JSON.stringify(mockAdvisorContext.unresolvedGaps))
)

// Multi-tab conversation message threads matching Figma mockups
const chatMessages = ref<DisplayMessage[]>([
  // Supervisor tab
  {
    id: 'msg-sup-1',
    tabId: 'supervisor',
    sender: 'agent',
    agentInitial: 'S',
    agentName: 'Supervisor',
    roleBadge: 'Gathering context',
    text: 'Atlas Service has 48 code files, FastAPI + React, 6 test files / 42 source files, and a build.yml with a build job but no detected test or deploy job. We\'ll start with ways of working, pain points and AI readiness.',
    timestamp: '09:41'
  },
  {
    id: 'msg-sup-2',
    tabId: 'supervisor',
    sender: 'agent',
    agentInitial: 'S',
    agentName: 'Supervisor',
    roleBadge: 'Context gathered',
    text: 'The conversation has captured ways of working, pain points and AI readiness. Specialist agents can now examine evidence, flag unresolved gaps, and ask targeted follow-up questions before the diagnostic is generated.',
    timestamp: '09:50'
  },

  // Requirements & Design tab
  {
    id: 'msg-req-1',
    tabId: 'requirements',
    sender: 'agent',
    agentInitial: 'R',
    agentName: 'Requirements & Design',
    roleBadge: 'Needs clarification',
    text: 'Can you confirm whether acceptance criteria are documented consistently across the team and whether design decisions are captured somewhere the delivery team can reference?',
    timestamp: '09:42'
  },
  {
    id: 'msg-req-2',
    tabId: 'requirements',
    sender: 'user',
    agentInitial: 'TL',
    agentName: 'Team representative',
    roleBadge: 'Response',
    text: 'We use Scrum. Acceptance criteria are usually documented in Jira, but design decisions are often captured in notes from review sessions and not always linked back to the implementation. We selected ambiguous acceptance criteria and undocumented decisions as pain points.',
    timestamp: '09:43'
  },

  // Code & Refactoring tab
  {
    id: 'msg-code-1',
    tabId: 'code',
    sender: 'agent',
    agentInitial: 'C',
    agentName: 'Code & Refactoring',
    roleBadge: 'Needs clarification',
    text: 'You mentioned repetitive implementation. Is that mostly in the Python service, the React frontend, or both? Are there any areas where the team feels the codebase is already too complex to refactor without more evidence?',
    timestamp: '09:44'
  },
  {
    id: 'msg-code-2',
    tabId: 'code',
    sender: 'user',
    agentInitial: 'TL',
    agentName: 'Team representative',
    roleBadge: 'Response',
    text: 'Repetitive implementation is more visible in the Python service. We also selected manual regression and low CI test confidence as pain points because tests run locally, but we expect them to run in CI and have not verified the workflow yet.',
    timestamp: '09:45'
  },

  // QA & Testing tab
  {
    id: 'msg-qa-1',
    tabId: 'testing',
    sender: 'agent',
    agentInitial: 'Q',
    agentName: 'QA & Testing',
    roleBadge: 'Needs clarification',
    text: 'Are the 6 test files / 42 source files mostly unit tests, integration tests, or end-to-end tests? Does the team rely on any external testing workflows that are not visible in this repository?',
    timestamp: '09:46'
  },
  {
    id: 'msg-qa-2',
    tabId: 'testing',
    sender: 'user',
    agentInitial: 'TL',
    agentName: 'Team representative',
    roleBadge: 'Response',
    text: 'The test files are mostly unit and integration tests. We do expect CI tests, but the workflow was not verified. Monitoring is managed outside this repository, which is why we also selected noisy alerts and manual release checklist as pain points.',
    timestamp: '09:47'
  },

  // DevOps & Monitoring tab
  {
    id: 'msg-devops-1',
    tabId: 'devops',
    sender: 'agent',
    agentInitial: 'D',
    agentName: 'DevOps & Monitoring',
    roleBadge: 'Needs clarification',
    text: 'Is the manual release checklist used for every deployment, or only for production? Are there any external monitoring dashboards or alerting rules that the diagnostic should reference before making recommendations?',
    timestamp: '09:48'
  },
  {
    id: 'msg-devops-2',
    tabId: 'devops',
    sender: 'user',
    agentInitial: 'TL',
    agentName: 'Team representative',
    roleBadge: 'Response',
    text: 'The checklist is mainly used for production. Monitoring lives outside this repository, which is why we mentioned noisy alerts. We are using GitHub Copilot in a pilot and ChatGPT for non-code drafting, but AI adoption is still exploratory.',
    timestamp: '09:49'
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

onMounted(async () => {
  store.ensureSampleSignals()
  store.setStep(3)

  // Real repo adaptation for the initial Supervisor greeting if available
  if (store.repoSignals && !isMock.value) {
    const s = store.repoSignals
    const supMsg = chatMessages.value.find((m) => m.id === 'msg-sup-1')
    if (supMsg) {
      supMsg.text = `${s.repoName} has ${s.totalSupportedFiles} code files, ${s.stack.frameworks.join(' + ') || 'modern frameworks'}, ${s.quality.testFilesCount} test files / ${s.quality.sourceFilesCount} source files. We'll start with ways of working, pain points and AI readiness.`
    }
  }

  // Real backend initialization if connected
  if (!api.USE_MOCKS && store.sessionId) {
    try {
      const diagRes = await api.backendClient.startDiagnostic(store.sessionId)
      if (diagRes.initial_messages && diagRes.initial_messages.length > 0) {
        diagRes.initial_messages.forEach((m) => {
          let tabId: TabKey = 'supervisor'
          let agentName = m.agent_label || 'Specialist'
          let initial = 'A'
          let roleBadge = 'Specialist agent'

          if (m.role === 'supervisor') {
            tabId = 'supervisor'
            agentName = 'Supervisor'
            initial = 'S'
            roleBadge = 'Gathering context'
          } else if (m.agent_domain) {
            initial = m.agent_domain.charAt(0).toUpperCase()
            roleBadge = `${m.agent_label || 'Specialist'} · Needs clarification`
            if (m.agent_domain.includes('req')) tabId = 'requirements'
            else if (m.agent_domain.includes('code')) tabId = 'code'
            else if (m.agent_domain.includes('test') || m.agent_domain.includes('qa')) tabId = 'testing'
            else if (m.agent_domain.includes('devops')) tabId = 'devops'
          }

          chatMessages.value.push({
            id: m.id,
            tabId,
            sender: m.role === 'user' ? 'user' : 'agent',
            agentInitial: initial,
            agentName,
            roleBadge,
            text: m.content,
            timestamp: m.timestamp
              ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : '09:41'
          })
        })
      }

      const gapsRes = await api.backendClient.getKnowledgeGaps(store.sessionId)
      if (gapsRes && gapsRes.gaps) {
        const gapList: UnresolvedKnowledgeGap[] = []
        let idx = 1
        for (const [domain, descriptions] of Object.entries(gapsRes.gaps)) {
          if (Array.isArray(descriptions)) {
            descriptions.forEach((desc: string) => {
              gapList.push({
                id: `gap-${idx++}`,
                title: `${domain.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())} gap`,
                description: desc,
                status: 'Open'
              })
            })
          }
        }
        if (gapList.length > 0) {
          knowledgeGaps.value = gapList
        }
      }
    } catch (err) {
      console.warn('Backend diagnostic load failed, falling back to local state:', err)
    }
  }

  scrollToBottom()
})

// Sending message from composer
async function handleSendMessage() {
  const text = composerInput.value.trim()
  if (!text || store.isLoading) return

  const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  // Append user response to active tab thread
  chatMessages.value.push({
    id: `msg-user-${Date.now()}`,
    tabId: activeTab.value,
    sender: 'user',
    agentInitial: 'TL',
    agentName: 'Team representative',
    roleBadge: 'Response',
    text,
    timestamp: now
  })

  composerInput.value = ''
  scrollToBottom()

  // Real backend turn if connected
  if (!api.USE_MOCKS && store.sessionId) {
    try {
      const res = await api.backendClient.sendConversationMessage(store.sessionId, text)
      if (res.new_messages && res.new_messages.length > 0) {
        res.new_messages.forEach((m) => {
          let tabId: TabKey = activeTab.value
          if (m.role === 'supervisor') tabId = 'supervisor'
          else if (m.agent_domain?.includes('req')) tabId = 'requirements'
          else if (m.agent_domain?.includes('code')) tabId = 'code'
          else if (m.agent_domain?.includes('test') || m.agent_domain?.includes('qa')) tabId = 'testing'
          else if (m.agent_domain?.includes('devops')) tabId = 'devops'

          chatMessages.value.push({
            id: m.id,
            tabId,
            sender: m.role === 'user' ? 'user' : 'agent',
            agentInitial: m.role === 'supervisor' ? 'S' : m.agent_domain?.charAt(0).toUpperCase() || 'A',
            agentName: m.agent_label || (m.role === 'supervisor' ? 'Supervisor' : 'Specialist Agent'),
            roleBadge: m.role === 'supervisor' ? 'Supervisor synthesis' : 'Specialist clarification',
            text: m.content,
            timestamp: now
          })
        })
      }
      scrollToBottom()
    } catch (err) {
      console.warn('Failed to send conversation message to backend:', err)
    }
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendMessage()
  }
}

async function handleSaveDraft() {
  draftSavedMessage.value = 'Saving...'
  if (!api.USE_MOCKS && store.sessionId) {
    try {
      await api.backendClient.saveDraft(store.sessionId, chatMessages.value)
    } catch {
      // Ignored
    }
  }
  setTimeout(() => {
    draftSavedMessage.value = 'Draft saved'
    setTimeout(() => {
      draftSavedMessage.value = ''
    }, 2000)
  }, 350)
}

// Proceed to diagnostic report
async function handleGenerateDiagnostic() {
  await store.generateDiagnosticReport()
  if (store.hasDiagnostic && !store.error) {
    router.push('/report')
  }
}

function goBackToSignals() {
  store.setStep(2)
  router.push('/signals')
}
</script>

<template>
  <div class="questions-view container">
    <!-- Top Mock Banner (gated on isMock) -->
    <div v-if="isMock" class="sample-data-banner">
      <span class="sample-tag">Sample data</span>
      Illustrative project, repository signals, team inputs and recommendations. Static preview only.
    </div>

    <!-- Top Step Meta Header -->
    <div class="screen-meta">
      <span class="step-badge">TEAM DIAGNOSTIC / STEP 3 OF 4</span>
      <h1 class="page-title">Clarify the team context with the diagnostic agents</h1>
      <p class="page-subtitle">
        The supervisor coordinates questions from four specialist agents. Answer the open questions,
        review the evidence being examined, and continue the conversation until the diagnostic is ready.
      </p>
    </div>

    <!-- 2-Column Chat & Side Panel Grid -->
    <div class="questions-grid">
      <!-- Left Column: Diagnostic conversation, Message composer & Path to diagnostic -->
      <section class="chat-column">
        <!-- 1. Unified Diagnostic Conversation Card -->
        <div class="card chat-card-container">
          <!-- Chat Header -->
          <div class="chat-header">
            <div>
              <h2 class="chat-box-title">Diagnostic conversation</h2>
              <p class="chat-box-desc">Supervisor coordinates questions from Requirements, Code, QA and DevOps.</p>
            </div>
            <span class="badge badge-purple">4 active agents</span>
          </div>

          <!-- Specialist Navigation Tabs -->
          <div class="chat-tabs-bar" role="tablist" aria-label="Specialist chat tabs">
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

          <!-- Messages Stream (Fixed height 380px, vertical scroll, anchored to bottom) -->
          <div
            ref="messagesContainer"
            class="messages-stream"
            aria-label="Conversation messages"
          >
            <div class="messages-inner-anchor">
              <ChatMessage
                v-for="msg in currentTabMessages"
                :key="msg.id"
                :sender="msg.sender"
                :agent-initial="msg.agentInitial"
                :agent-name="msg.agentName"
                :role-badge="msg.roleBadge"
                :text="msg.text"
                :timestamp="msg.timestamp"
                :is-skipped="msg.isSkipped"
              />
            </div>
          </div>

          <!-- Input Bar (Separated from messages area by a thin border) -->
          <div class="chat-input-bar-container">
            <div class="input-bar-row">
              <textarea
                v-model="composerInput"
                rows="2"
                class="chat-input-textarea"
                placeholder="Add a note, ask a question, or clarify a pain point"
                :disabled="store.isLoading"
                aria-label="Add a note or response to the agent"
                @keydown="handleKeyDown"
              ></textarea>
              <button
                type="button"
                class="btn-primary input-send-btn"
                :disabled="store.isLoading || !composerInput.trim()"
                @click="handleSendMessage"
              >
                Send
              </button>
            </div>

            <!-- Small helper text row under the input bar -->
            <div class="input-helpers-row">
              <span class="footnote-text">
                <template v-if="isMock">Sample data · </template>Keep it concise. Do not include personal data, client identifiers, secrets or sensitive source code. Remove sensitive details before submitting.
              </span>
              <span class="draft-indicator">Draft saved automatically</span>
            </div>
          </div>
        </div>

        <!-- 2. Path to an evolving diagnostic Card (Unchanged separate card below chat) -->
        <div class="card evolving-card">
          <h3 class="evolving-title">Path to an evolving diagnostic</h3>
          <p class="evolving-desc">
            Continue the conversation, answer follow-up questions, and review specialist findings. The diagnostic will evolve as the team provides more context.
          </p>

          <div class="evolving-actions">
            <button type="button" class="btn-secondary" @click="goBackToSignals">
              Back
            </button>
            <button type="button" class="btn-secondary" @click="handleSaveDraft">
              {{ draftSavedMessage || 'Save draft' }}
            </button>
            <button
              type="button"
              class="btn-primary continue-btn"
              :disabled="store.isLoading"
              @click="handleGenerateDiagnostic"
            >
              Continue diagnostic
            </button>
          </div>

          <div class="evolving-footer">
            <span class="footnote-text">
              <template v-if="isMock">Sample data · </template>The diagnostic is not final. You can keep chatting, question the project, and edit the report before it is shared.
            </span>
          </div>
        </div>
      </section>

      <!-- Right Column: Context, Specialist Activity & Knowledge Gaps -->
      <TopicsProgress
        :signals="store.repoSignals || undefined"
        :active-tab="activeTab"
        :specialists="specialists"
        :knowledge-gaps="knowledgeGaps"
        :is-mock="isMock"
      />
    </div>
  </div>
</template>

<style scoped>
.questions-view {
  padding-top: 1.5rem;
  padding-bottom: 4rem;
}

/* Top Sample Banner */
.sample-data-banner {
  background-color: #faf5ff;
  border: 1px solid #e9d5ff;
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  font-size: 0.8125rem;
  color: #6b21a8;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sample-tag {
  font-weight: 700;
  color: #581c87;
}

.screen-meta {
  margin-bottom: 1.75rem;
}

.step-badge {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-primary);
  margin-bottom: 0.5rem;
  display: block;
}

.page-title {
  font-size: 2.25rem;
  font-weight: 800;
  letter-spacing: -0.025em;
  color: var(--color-text-primary);
  margin-bottom: 0.5rem;
}

.page-subtitle {
  font-size: 1rem;
  color: var(--color-text-secondary);
  max-width: 820px;
  line-height: 1.5;
}

/* 2-Column Grid */
.questions-grid {
  display: grid;
  grid-template-columns: 1.65fr 1fr;
  gap: 1.75rem;
  align-items: start;
}

.chat-column {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.card {
  padding: 1.5rem;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

/* 1. Chat Container */
.chat-card-container {
  display: flex;
  flex-direction: column;
  gap: 1.125rem;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-box-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.chat-box-desc {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin-top: 0.125rem;
}

/* Specialist Tabs Bar */
.chat-tabs-bar {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  background-color: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: var(--radius-md);
  padding: 0.25rem;
  overflow-x: auto;
}

.chat-tab-btn {
  background: transparent;
  border: none;
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  padding: 0.4375rem 0.875rem;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  min-height: auto;
}

.chat-tab-btn:hover:not(.tab-active) {
  color: var(--color-text-primary);
  background-color: #f1f5f9;
}

.chat-tab-btn.tab-active {
  background-color: var(--color-primary);
  color: #ffffff;
}

/* Messages Stream: Fixed height 380px, internal vertical scroll, messages anchored to bottom */
.messages-stream {
  height: 380px;
  overflow-y: auto;
  padding-right: 0.5rem;
  scroll-behavior: smooth;
  display: flex;
  flex-direction: column;
}

.messages-inner-anchor {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Integrated Chat Input Bar */
.chat-input-bar-container {
  border-top: 1px solid var(--color-border);
  padding-top: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.input-bar-row {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
}

.chat-input-textarea {
  flex: 1;
  min-height: 44px;
  max-height: 120px;
  padding: 0.625rem 0.875rem;
  font-family: inherit;
  font-size: 0.9375rem;
  color: var(--color-text-primary);
  background-color: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  resize: vertical;
  line-height: 1.45;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.chat-input-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.input-send-btn {
  min-height: 44px;
  padding: 0.625rem 1.375rem;
  font-weight: 600;
}

.input-helpers-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.draft-indicator {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.evolving-footer {
  border-top: 1px solid var(--color-border-subtle);
  padding-top: 0.625rem;
}

.footnote-text {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.4;
}

/* 3. Path to Evolving Diagnostic Card */
.evolving-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.evolving-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.evolving-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

.evolving-actions {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-top: 0.25rem;
  margin-bottom: 0.5rem;
}

.continue-btn {
  font-weight: 600;
}

@media (max-width: 980px) {
  .questions-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .page-title {
    font-size: 1.75rem;
  }

  .input-bar-row {
    flex-direction: column;
    align-items: stretch;
  }

  .evolving-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
