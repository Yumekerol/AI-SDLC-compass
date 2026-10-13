<script setup lang="ts">
import { ref } from 'vue'
import type { SuggestionChipItem } from '@/types/questions'
import SuggestionChip from '@/components/common/SuggestionChip.vue'

defineProps<{
  chips: SuggestionChipItem[]
  placeholder?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', text: string): void
  (e: 'skip'): void
}>()

const inputText = ref('')

function handleChipSelect(chip: SuggestionChipItem) {
  // Directly send or fill chip value
  emit('submit', chip.value)
  inputText.value = ''
}

function handleSend() {
  const trimmed = inputText.value.trim()
  if (trimmed) {
    emit('submit', trimmed)
    inputText.value = ''
  }
}

function handleSkip() {
  emit('skip')
  inputText.value = ''
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="chat-composer-box card">
    <!-- Suggestion Chips Row -->
    <div v-if="chips && chips.length > 0" class="chips-section">
      <span class="chips-label">Optional suggestions:</span>
      <div class="chips-list" role="group" aria-label="Quick answer suggestions">
        <SuggestionChip
          v-for="chip in chips"
          :key="chip.id"
          :label="chip.label"
          :disabled="disabled"
          @select="handleChipSelect(chip)"
        />
      </div>
    </div>

    <!-- Text Composer -->
    <div class="composer-input-row">
      <div class="textarea-wrapper">
        <textarea
          v-model="inputText"
          rows="2"
          class="chat-textarea"
          :placeholder="placeholder || 'Type your team\'s response or context...'"
          :disabled="disabled"
          aria-label="Your response to the diagnostic question"
          @keydown="handleKeyDown"
        ></textarea>
      </div>

      <div class="composer-action-buttons">
        <button
          type="button"
          class="btn-ghost skip-btn"
          :disabled="disabled"
          @click="handleSkip"
        >
          Skip question
        </button>

        <button
          type="button"
          class="btn-primary send-btn"
          :disabled="disabled || !inputText.trim()"
          @click="handleSend"
        >
          <span>Send</span>
          <svg class="send-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path
              d="M15.964.686a.5.5 0 0 0-.65-.65L.767 5.855H.766l-.452.18a.5.5 0 0 0-.082.887l.41.26.001.002 4.995 3.178 3.178 4.995.002.002.26.41a.5.5 0 0 0 .886-.083l6-15Zm-1.833 1.89L6.637 10.074l-3.39-2.156 10.884-5.342Zm-2.564 3.39-7.5 7.5-.001-.001 2.156-3.39 5.345-4.109Z"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- Composer Privacy & Instructions Note -->
    <div class="composer-note">
      <span>Sample data · Keep it concise. Do not include personal credentials, client secrets, or full source code.</span>
    </div>
  </div>
</template>

<style scoped>
.chat-composer-box {
  padding: 1.25rem 1.5rem;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chips-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.chips-label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.chips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.composer-input-row {
  display: flex;
  align-items: flex-end;
  gap: 0.875rem;
}

.textarea-wrapper {
  flex: 1;
}

.chat-textarea {
  width: 100%;
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

.chat-textarea:focus {
  outline: none;
  background-color: #ffffff;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.composer-action-buttons {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.skip-btn {
  font-size: 0.875rem;
  min-height: var(--min-touch-target);
  padding: 0.625rem 1rem;
  color: var(--color-text-muted);
}

.skip-btn:hover:not(:disabled) {
  color: var(--color-text-primary);
  background-color: #f1f5f9;
}

.send-btn {
  min-height: var(--min-touch-target);
  padding: 0.625rem 1.25rem;
}

.send-icon {
  width: 14px;
  height: 14px;
}

.composer-note {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border-subtle);
  padding-top: 0.5rem;
}

@media (max-width: 640px) {
  .composer-input-row {
    flex-direction: column;
    align-items: stretch;
  }

  .composer-action-buttons {
    justify-content: space-between;
  }
}
</style>
