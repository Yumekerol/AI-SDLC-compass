<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import * as api from '@/api'
import type { Question, TopicProgress, UserAnswer } from '@/types/questions'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import TopicsProgress from '@/components/chat/TopicsProgress.vue'

const router = useRouter()
const store = useSessionStore()

interface DisplayMessage {
  id: string
  sender: 'agent' | 'user'
  agentInitial?: string
  agentName: string
  roleBadge?: string
  text: string
  timestamp: string
  isSkipped?: boolean
}

const questionsList = ref<Question[]>([])
const currentQuestionIndex = ref<number>(0)
const chatMessages = ref<DisplayMessage[]>([])
const topics = ref<TopicProgress[]>([])

onMounted(async () => {
  store.ensureSampleSignals()
  store.setStep(3)

  try {
    questionsList.value = await api.getQuestions()
  } catch {
    // Fallback if network was simulated
    questionsList.value = []
  }

  // Build initial topics progress
  topics.value = questionsList.value.map((q, idx) => ({
    id: q.id,
    name: q.topic,
    status: idx === 0 ? 'current' : 'pending'
  }))

  // Initial welcome message from Supervisor
  chatMessages.value.push({
    id: 'msg-supervisor-welcome',
    sender: 'agent',
    agentInitial: 'S',
    agentName: 'Supervisor',
    roleBadge: 'Gathering context',
    text: `Atlas Service has 48 code files, FastAPI + React, 6 test files / 42 source files, and a build.yml with a build job but no detected test or deploy job. We'll start with ways of working, pain points and AI readiness.`,
    timestamp: '09:41'
  })

  // Post the first question
  if (questionsList.value.length > 0) {
    postAgentQuestion(0)
  }
})

const currentQuestion = computed<Question | null>(() => {
  if (currentQuestionIndex.value < questionsList.value.length) {
    return questionsList.value[currentQuestionIndex.value]
  }
  return null
})

const isAllAnswered = computed(() => {
  return currentQuestionIndex.value >= questionsList.value.length
})

const answeredCount = computed(() => {
  return store.answersList.length
})

const totalQuestions = computed(() => {
  return questionsList.value.length
})

function getAgentInitial(role: string): string {
  if (role.includes('Requirements')) return 'R'
  if (role.includes('Code')) return 'C'
  if (role.includes('QA')) return 'Q'
  if (role.includes('DevOps')) return 'D'
  return 'A'
}

function postAgentQuestion(index: number) {
  const q = questionsList.value[index]
  if (!q) return

  const initial = getAgentInitial(q.agentRole)
  chatMessages.value.push({
    id: `msg-question-${q.id}`,
    sender: 'agent',
    agentInitial: initial,
    agentName: q.agentName,
    roleBadge: `${q.agentRole} · Needs clarification`,
    text: q.text,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  })
}

// User submits an answer (via suggestion chip or typed input)
async function handleUserAnswer(answerText: string) {
  if (!currentQuestion.value) return

  const activeQ = currentQuestion.value
  const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  // 1. Append user message to UI
  chatMessages.value.push({
    id: `msg-user-${activeQ.id}`,
    sender: 'user',
    agentName: 'Team representative',
    roleBadge: 'Response',
    text: answerText,
    timestamp: now,
    isSkipped: false
  })

  // 2. Persist in Pinia store
  const answerPayload: UserAnswer = {
    questionId: activeQ.id,
    topic: activeQ.topic,
    answerText,
    skipped: false,
    timestamp: now
  }
  await store.recordAnswer(answerPayload)

  // 3. Mark current topic as completed
  if (topics.value[currentQuestionIndex.value]) {
    topics.value[currentQuestionIndex.value].status = 'completed'
  }

  // 4. Advance to next question
  advanceNextQuestion()
}

// User skips the question
async function handleUserSkip() {
  if (!currentQuestion.value) return

  const activeQ = currentQuestion.value
  const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  // 1. Append skipped message to UI
  chatMessages.value.push({
    id: `msg-user-skipped-${activeQ.id}`,
    sender: 'user',
    agentName: 'Team representative',
    roleBadge: 'Response',
    text: 'Question skipped. Proceeding without team input on this topic.',
    timestamp: now,
    isSkipped: true
  })

  // 2. Persist skipped answer in Pinia store
  await store.skipQuestion(activeQ.id, activeQ.topic)

  // 3. Mark topic completed (skipped)
  if (topics.value[currentQuestionIndex.value]) {
    topics.value[currentQuestionIndex.value].status = 'completed'
  }

  // 4. Advance
  advanceNextQuestion()
}

function advanceNextQuestion() {
  currentQuestionIndex.value++

  if (currentQuestionIndex.value < questionsList.value.length) {
    if (topics.value[currentQuestionIndex.value]) {
      topics.value[currentQuestionIndex.value].status = 'current'
    }
    // Simulate brief agent response delay
    setTimeout(() => {
      postAgentQuestion(currentQuestionIndex.value)
    }, 400)
  } else {
    // All done!
    setTimeout(() => {
      chatMessages.value.push({
        id: 'msg-supervisor-done',
        sender: 'agent',
        agentInitial: 'S',
        agentName: 'Supervisor',
        roleBadge: 'Context gathered',
        text: 'All clarification questions are answered! The specialist agents now have sufficient contextual evidence to synthesize a grounded 6-phase SDLC diagnostic.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      })
    }, 400)
  }
}

// Proceed to diagnostic synthesis
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
    <!-- Top Step Meta Header -->
    <div class="screen-meta">
      <span class="step-badge">TEAM DIAGNOSTIC / STEP 3 OF 5</span>
      <h1 class="page-title">Clarify the team context with the diagnostic agents</h1>
      <p class="page-subtitle">
        The supervisor coordinates questions from four specialist agents. Answer the open questions,
        review the evidence being examined, and continue until your diagnostic is synthesized.
      </p>
    </div>

    <!-- 2-Column Chat & Side Panel Grid -->
    <div class="questions-grid">
      <!-- Left Column: Interactive Chat Conversation -->
      <section class="chat-column">
        <!-- Chat Header Banner -->
        <div class="card chat-card-container">
          <div class="chat-header">
            <div>
              <h2 class="chat-box-title">Diagnostic conversation</h2>
              <p class="chat-box-desc">Supervisor coordinates questions from Requirements, Code, QA and DevOps.</p>
            </div>
            <span class="badge badge-purple">4 active agents</span>
          </div>

          <!-- Messages Stream -->
          <div class="messages-stream" aria-label="Conversation messages">
            <ChatMessage
              v-for="msg in chatMessages"
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

          <!-- Active Question Composer (Only when questions remain) -->
          <div v-if="!isAllAnswered && currentQuestion" class="composer-container">
            <ChatInput
              :chips="currentQuestion.suggestionChips"
              :placeholder="currentQuestion.placeholder"
              :disabled="store.isLoading"
              @submit="handleUserAnswer"
              @skip="handleUserSkip"
            />
          </div>

          <!-- Completion Banner when all questions answered or skipped -->
          <div v-else class="all-answered-banner card">
            <div class="banner-icon-circle" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path
                  fill-rule="evenodd"
                  d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                  clip-rule="evenodd"
                />
              </svg>
            </div>
            <div class="banner-body">
              <h3 class="banner-title">Conversation completed</h3>
              <p class="banner-desc">
                Your team context has been integrated with the repository evidence.
                Generate the diagnostic report to review phase-by-phase recommendations.
              </p>
            </div>
            <button
              type="button"
              class="btn-primary banner-action-btn"
              :disabled="store.isLoading"
              @click="handleGenerateDiagnostic"
            >
              Generate diagnostic report
            </button>
          </div>
        </div>
      </section>

      <!-- Right Column: Topics Side Panel -->
      <TopicsProgress
        :topics="topics"
        :signals="store.repoSignals || undefined"
        :answered-count="answeredCount"
        :total-count="totalQuestions"
        :can-generate="answeredCount > 0 || isAllAnswered"
        @generate="handleGenerateDiagnostic"
        @back="goBackToSignals"
      />
    </div>
  </div>
</template>

<style scoped>
.questions-view {
  padding-top: 2.25rem;
  padding-bottom: 4rem;
}

.screen-meta {
  margin-bottom: 2rem;
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
  font-size: 1.0625rem;
  color: var(--color-text-secondary);
  max-width: 780px;
}

/* 2-Column Grid */
.questions-grid {
  display: grid;
  grid-template-columns: 1.7fr 1fr;
  gap: 2rem;
  align-items: start;
}

.chat-column {
  display: flex;
  flex-direction: column;
}

.chat-card-container {
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.chat-box-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.chat-box-desc {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.messages-stream {
  display: flex;
  flex-direction: column;
  min-height: 380px;
  max-height: 600px;
  overflow-y: auto;
  padding-right: 0.5rem;
  scroll-behavior: smooth;
}

.composer-container {
  margin-top: auto;
}

/* All Answered Finish Banner */
.all-answered-banner {
  background-color: var(--color-primary-light);
  border-color: var(--color-primary-border);
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.banner-icon-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background-color: var(--color-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.banner-icon-circle svg {
  width: 22px;
  height: 22px;
}

.banner-body {
  flex: 1;
}

.banner-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 0.25rem;
}

.banner-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.banner-action-btn {
  white-space: nowrap;
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

  .chat-card-container {
    padding: 1.25rem;
  }

  .all-answered-banner {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }

  .banner-icon-circle {
    margin: 0 auto;
  }
}
</style>
