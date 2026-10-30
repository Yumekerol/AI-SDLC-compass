<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useDiagnosticStore } from '@/stores/diagnostic'
import * as api from '@/api'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import TopicsProgress from '@/components/chat/TopicsProgress.vue'

const router = useRouter()
const store = useSessionStore()
const diagnostic = useDiagnosticStore()

const composerInput = ref('')
const draftSavedMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)

const isMock = computed(() => store.isMock)

// The report can only be generated once every specialist has finished.
const canContinue = computed(
  () => api.USE_MOCKS || (diagnostic.status === 'report_ready' && !diagnostic.processing)
)

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => diagnostic.messages.length, scrollToBottom)
watch(() => diagnostic.processing, scrollToBottom)

onMounted(async () => {
  store.setStep(3)
  await store.ensureSampleSignals()
  await diagnostic.load()
  scrollToBottom()
})

async function handleSendMessage() {
  const text = composerInput.value.trim()
  if (!text || diagnostic.processing) return
  composerInput.value = ''
  await diagnostic.sendMessage(text)
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
      await api.backendClient.saveDraft(store.sessionId, diagnostic.messages)
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
        Four specialists review the repository one after another and ask you a question when the code
        alone doesn't tell them enough. Answer in the chat; the report is ready once all four are done.
      </p>
    </div>

    <!-- 2-Column Chat & Side Panel Grid -->
    <div class="questions-grid">
      <section class="chat-column">
        <!-- One conversation: every agent's questions, in order -->
        <div class="card chat-card-container">
          <div class="chat-header">
            <div>
              <h2 class="chat-box-title">Diagnostic conversation</h2>
              <p class="chat-box-desc">The specialists ask their questions here, one at a time.</p>
            </div>
          </div>

          <div ref="messagesContainer" class="messages-stream" aria-label="Conversation messages" aria-live="polite">
            <div class="messages-inner-anchor">
              <p v-if="!diagnostic.messages.length && !diagnostic.error" class="empty-chat">
                Starting the diagnostic…
              </p>
              <ChatMessage
                v-for="msg in diagnostic.messages"
                :key="msg.id"
                :sender="msg.sender"
                :agent-initial="msg.agentInitial"
                :agent-name="msg.agentName"
                :text="msg.text"
                :timestamp="msg.timestamp"
              />
              <div v-if="diagnostic.processing" class="agent-status-row">
                <span class="typing-dots" aria-hidden="true"><span></span><span></span><span></span></span>
                <span class="status-text">{{ diagnostic.statusText }}</span>
                <button type="button" class="link-btn" @click="diagnostic.cancel()">Stop</button>
              </div>
              <div v-else-if="diagnostic.status === 'cancelled' || diagnostic.status === 'error'" class="agent-status-row">
                <span class="status-text">The diagnostic is not running.</span>
                <button type="button" class="link-btn" @click="diagnostic.restart()">Restart diagnostic</button>
              </div>
              <p v-if="diagnostic.error" class="chat-error" role="alert">{{ diagnostic.error }}</p>
            </div>
          </div>

          <div class="chat-input-bar-container">
            <div class="input-bar-row">
              <textarea
                v-model="composerInput"
                rows="2"
                class="chat-input-textarea"
                :placeholder="diagnostic.processing ? 'Wait for the specialist to finish…' : 'Answer the question above'"
                :disabled="diagnostic.processing"
                aria-label="Your answer to the specialist"
                @keydown="handleKeyDown"
              ></textarea>
              <button
                type="button"
                class="btn-primary input-send-btn"
                :disabled="diagnostic.processing || !composerInput.trim()"
                @click="handleSendMessage"
              >
                Send
              </button>
            </div>

            <div class="input-helpers-row">
              <span class="footnote-text">
                <template v-if="isMock">Sample data · </template>Keep it concise. Do not include personal data, client identifiers, secrets or sensitive source code.
              </span>
            </div>
          </div>
        </div>

        <div class="card evolving-card">
          <h3 class="evolving-title">Path to an evolving diagnostic</h3>
          <p class="evolving-desc">
            <template v-if="canContinue">All specialists are done. Continue to review the diagnostic report.</template>
            <template v-else>The report becomes available once every specialist has finished.</template>
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
              :disabled="store.isLoading || !canContinue"
              @click="handleGenerateDiagnostic"
            >
              Continue diagnostic
            </button>
          </div>
        </div>
      </section>

      <!-- Right Column: Context, Specialist Activity & Knowledge Gaps -->
      <TopicsProgress
        :signals="store.repoSignals || undefined"
        :progress="diagnostic.progress"
        :knowledge-gaps="diagnostic.gaps"
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

/* Messages Stream: fixed height, internal vertical scroll, anchored to bottom */
.messages-stream {
  height: 440px;
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
  gap: 0.5rem;
}

/* Live status row under the last message while an agent works */
.agent-status-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  padding: 0.25rem 0.25rem 0;
}

.status-text {
  flex: 1;
}

.link-btn {
  background: none;
  border: none;
  padding: 0;
  min-height: auto;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  white-space: nowrap;
}

.link-btn:hover {
  text-decoration: underline;
}

.typing-dots {
  display: inline-flex;
  gap: 3px;
}

.typing-dots span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background-color: var(--color-primary);
  animation: blink 1.2s infinite ease-in-out;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes blink {
  0%,
  80%,
  100% {
    opacity: 0.25;
  }
  40% {
    opacity: 1;
  }
}

.chat-error {
  font-size: 0.8125rem;
  color: #b91c1c;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--radius-md);
  padding: 0.5rem 0.75rem;
}

.empty-chat {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  text-align: center;
  padding: 1rem 0;
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
