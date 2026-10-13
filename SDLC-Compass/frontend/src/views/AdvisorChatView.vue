<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import * as api from '@/api'
import type { AdvisorContext, AdvisorMessage } from '@/types/advisor'
import AdvisorContextPanel from '@/components/advisor/AdvisorContextPanel.vue'
import SuggestionChip from '@/components/common/SuggestionChip.vue'
import { mockAdvisorContext, mockInitialAdvisorMessages } from '@/mocks'

const router = useRouter()
const store = useSessionStore()

const context = ref<AdvisorContext>(JSON.parse(JSON.stringify(mockAdvisorContext)))
const messages = ref<AdvisorMessage[]>([])
const inputText = ref<string>('')
const isSending = ref<boolean>(false)
const chatScrollContainer = ref<HTMLElement | null>(null)

onMounted(async () => {
  store.ensureSampleSignals()
  store.setStep(5)

  try {
    const [loadedContext, loadedMessages] = await Promise.all([
      api.getAdvisorContext(),
      api.getAdvisorMessages()
    ])
    context.value = loadedContext
    messages.value = loadedMessages
  } catch {
    context.value = mockAdvisorContext
    messages.value = mockInitialAdvisorMessages
  }

  scrollToBottom()
})

function scrollToBottom() {
  nextTick(() => {
    if (chatScrollContainer.value) {
      chatScrollContainer.value.scrollTop = chatScrollContainer.value.scrollHeight
    }
  })
}

// Sending a message
async function handleSend(textToSend?: string) {
  const content = (textToSend || inputText.value).trim()
  if (!content || isSending.value) return

  inputText.value = ''
  isSending.value = true

  // 1. Optimistic user message addition
  const userMsg: AdvisorMessage = {
    id: `msg-user-${Date.now()}`,
    sender: 'user',
    senderName: 'Team representative',
    content,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  messages.value.push(userMsg)
  scrollToBottom()

  // 2. Call typed API
  try {
    const reply = await api.sendAdvisorMessage(content)
    messages.value.push(reply)
    scrollToBottom()
  } catch {
    // Graceful error notification if needed
  } finally {
    isSending.value = false
  }
}

function handleChipClick(chipText: string) {
  handleSend(chipText)
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleBackToReport() {
  store.setStep(4)
  router.push('/report')
}
</script>

<template>
  <div class="advisor-view container">
    <!-- Top Step Meta Header -->
    <div class="screen-meta">
      <span class="step-badge">TEAM DIAGNOSTIC / STEP 5 OF 5</span>
      <h1 class="page-title">Advisor conversation & context workspace</h1>
      <p class="page-subtitle">
        Engage with the specialist agents and the synthesizer. Challenge recommendations,
        inquire about implementation steps, or adjust priorities based on team realities.
      </p>
      <div class="preview-notice-badge">
        <svg class="preview-notice-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
            clip-rule="evenodd"
          />
        </svg>
        <span><strong>Preview:</strong> This conversational advisor is an interactive preview and is not yet connected to the backend.</span>
      </div>
    </div>

    <!-- 2-Column Layout: Left Context & Priorities, Right Conversation -->
    <div class="advisor-workspace-grid">
      <!-- Left Panel: Context, Priorities & Gaps -->
      <AdvisorContextPanel
        :context="context"
        :diagnostic-report="store.diagnostic"
        @back-to-report="handleBackToReport"
      />

      <!-- Right Panel: Conversation Stream with Suggestion Chips & Composer -->
      <section class="conversation-panel" aria-label="Advisor conversation">
        <div class="card chat-card">
          <!-- Chat Header -->
          <div class="chat-header">
            <div>
              <h2 class="chat-title">Advisory conversation</h2>
              <p class="chat-desc">
                Supervisor coordinates specialists from Requirements, Code, QA and DevOps. Synthesizer prioritises recommendations.
              </p>
            </div>
            <span class="badge badge-purple">4 active specialists</span>
          </div>

          <!-- Messages Stream Container -->
          <div
            ref="chatScrollContainer"
            class="messages-scroll-area"
            aria-label="Conversation stream"
          >
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="message-bubble-row"
              :class="{
                'msg-from-user': msg.sender === 'user',
                'msg-from-specialist': msg.sender === 'specialist',
                'msg-from-advisor': msg.sender === 'advisor'
              }"
            >
              <!-- Avatar -->
              <div
                class="bubble-avatar"
                :class="{
                  'avatar-user': msg.sender === 'user',
                  'avatar-specialist': msg.sender === 'specialist',
                  'avatar-advisor': msg.sender === 'advisor'
                }"
                aria-hidden="true"
              >
                <span>
                  {{
                    msg.sender === 'user'
                      ? 'TL'
                      : msg.senderName.charAt(0)
                  }}
                </span>
              </div>

              <!-- Message Body -->
              <div class="bubble-content-wrap">
                <div class="bubble-meta">
                  <strong class="author-name">{{ msg.senderName }}</strong>
                  <span v-if="msg.role" class="author-role">{{ msg.role }}</span>
                  <span class="message-time">{{ msg.timestamp }}</span>
                </div>

                <div class="bubble-body">
                  <p class="message-text">{{ msg.content }}</p>

                  <!-- Status Change Proposal Box (if present) -->
                  <div
                    v-if="msg.statusChangeProposal"
                    class="proposal-box"
                  >
                    <div class="proposal-top">
                      <span class="badge badge-success">Approved proposal</span>
                      <strong class="proposal-title">{{ msg.statusChangeProposal.title }}</strong>
                    </div>
                    <p class="proposal-reason">{{ msg.statusChangeProposal.reason }}</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Typing / Processing indicator -->
            <div v-if="isSending" class="message-bubble-row msg-from-advisor">
              <div class="bubble-avatar avatar-advisor" aria-hidden="true">
                <span>A</span>
              </div>
              <div class="bubble-content-wrap">
                <div class="bubble-body typing-body">
                  <span class="typing-indicator">Advisor is considering evidence...</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Tappable Suggestion Chips Bar -->
          <div class="chips-toolbar">
            <span class="chips-heading">Suggested questions:</span>
            <div class="chips-flex" role="group" aria-label="Suggested follow-up questions">
              <SuggestionChip
                v-for="(suggestion, idx) in context.suggestedQuestions"
                :key="idx"
                :label="suggestion"
                :disabled="isSending"
                @select="handleChipClick(suggestion)"
              />
            </div>
          </div>

          <!-- Message Composer Input -->
          <div class="composer-container">
            <div class="composer-input-row">
              <textarea
                v-model="inputText"
                rows="2"
                class="composer-textarea"
                placeholder="Ask a follow-up question, challenge a recommendation or edit a report section..."
                aria-label="Ask a follow-up question"
                :disabled="isSending"
                @keydown="handleKeyDown"
              ></textarea>

              <button
                type="button"
                class="btn-primary send-btn"
                :disabled="isSending || !inputText.trim()"
                @click="handleSend()"
              >
                <span>Send</span>
                <svg class="send-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path
                    d="M15.964.686a.5.5 0 0 0-.65-.65L.767 5.855H.766l-.452.18a.5.5 0 0 0-.082.887l.41.26.001.002 4.995 3.178 3.178 4.995.002.002.26.41a.5.5 0 0 0 .886-.083l6-15Zm-1.833 1.89L6.637 10.074l-3.39-2.156 10.884-5.342Zm-2.564 3.39-7.5 7.5-.001-.001 2.156-3.39 5.345-4.109Z"
                  />
                </svg>
              </button>
            </div>

            <span class="composer-privacy-note">
              Sample data · Keep it concise. Do not include personal data, client identifiers, secrets or sensitive source code.
            </span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.advisor-view {
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
  max-width: 800px;
}

.preview-notice-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.5rem 0.875rem;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}

.preview-notice-icon {
  width: 1rem;
  height: 1rem;
  color: var(--color-primary);
  flex-shrink: 0;
}

/* 2-Column Workspace Grid */
.advisor-workspace-grid {
  display: grid;
  grid-template-columns: 1fr 1.7fr;
  gap: 2rem;
  align-items: start;
}

/* Right Column: Chat Card */
.conversation-panel {
  display: flex;
  flex-direction: column;
}

.chat-card {
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.chat-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.chat-desc {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.messages-scroll-area {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  min-height: 420px;
  max-height: 600px;
  overflow-y: auto;
  padding-right: 0.5rem;
  scroll-behavior: smooth;
}

/* Message Bubble */
.message-bubble-row {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
  animation: fadeIn 0.2s ease-out;
}

.bubble-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8125rem;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
}

.avatar-specialist {
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  border: 1px solid var(--color-primary-border);
}

.avatar-advisor {
  background-color: #f5f3ff;
  color: #7c3aed;
  border: 1px solid #ddd6fe;
}

.avatar-user {
  background-color: #f1f5f9;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.bubble-content-wrap {
  flex: 1;
  max-width: 90%;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.bubble-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.author-name {
  color: var(--color-text-primary);
}

.author-role {
  font-size: 0.6875rem;
  color: var(--color-primary);
  background-color: var(--color-primary-light);
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
}

.message-time {
  color: var(--color-text-muted);
  font-size: 0.75rem;
  margin-left: auto;
}

.bubble-body {
  padding: 1rem 1.25rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background-color: var(--color-surface);
  box-shadow: var(--shadow-sm);
  line-height: 1.5;
}

.msg-from-user .bubble-body {
  background-color: #f8fafc;
  border-color: var(--color-border-strong);
}

.msg-from-advisor .bubble-body {
  background-color: #faf5ff;
  border-color: #e9d5ff;
}

.message-text {
  font-size: 0.9375rem;
  color: var(--color-text-primary);
}

.typing-body {
  background-color: #fafbfc;
  font-style: italic;
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

/* Proposal Box inside Bubble */
.proposal-box {
  margin-top: 0.75rem;
  padding: 0.75rem 1rem;
  background-color: #ffffff;
  border: 1px solid #d8b4fe;
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.proposal-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.proposal-title {
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.proposal-reason {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}

/* Suggestion Chips Toolbar */
.chips-toolbar {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border-subtle);
}

.chips-heading {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.chips-flex {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

/* Message Composer Input */
.composer-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.5rem;
}

.composer-input-row {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
}

.composer-textarea {
  flex: 1;
  min-height: 48px;
  max-height: 120px;
  padding: 0.75rem 1rem;
  font-family: inherit;
  font-size: 0.9375rem;
  color: var(--color-text-primary);
  background-color: #fafbfc;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  resize: vertical;
  line-height: 1.4;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.composer-textarea:focus {
  outline: none;
  background-color: #ffffff;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.send-btn {
  min-height: var(--min-touch-target);
  padding: 0.625rem 1.25rem;
}

.send-icon {
  width: 14px;
  height: 14px;
}

.composer-privacy-note {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 980px) {
  .advisor-workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .page-title {
    font-size: 1.75rem;
  }

  .chat-card {
    padding: 1.25rem;
  }

  .composer-input-row {
    flex-direction: column;
    align-items: stretch;
  }

  .send-btn {
    width: 100%;
  }
}
</style>
