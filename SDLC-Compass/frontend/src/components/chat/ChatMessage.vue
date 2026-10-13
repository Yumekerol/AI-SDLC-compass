<script setup lang="ts">
defineProps<{
  sender: 'agent' | 'user'
  agentInitial?: string
  agentName: string
  roleBadge?: string
  text: string
  timestamp?: string
  isSkipped?: boolean
}>()
</script>

<template>
  <div
    class="message-row"
    :class="{ 'message-user': sender === 'user', 'message-agent': sender === 'agent' }"
  >
    <!-- Avatar Circle -->
    <div
      class="avatar"
      :class="{
        'avatar-user': sender === 'user',
        'avatar-agent': sender === 'agent',
        'avatar-skipped': isSkipped
      }"
      aria-hidden="true"
    >
      <span>{{ agentInitial || (sender === 'user' ? 'TL' : 'S') }}</span>
    </div>

    <!-- Bubble Container -->
    <div class="bubble-container">
      <div class="bubble-header">
        <span class="sender-name">{{ agentName }}</span>
        <span v-if="roleBadge" class="badge-role">{{ roleBadge }}</span>
        <span v-if="isSkipped" class="badge-skipped">Skipped</span>
        <span v-if="timestamp" class="timestamp">{{ timestamp }}</span>
      </div>

      <div class="bubble-body" :class="{ 'body-skipped': isSkipped }">
        <p class="bubble-text">{{ text }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
  margin-bottom: 1.25rem;
  animation: fadeIn 0.2s ease-out;
}

.avatar {
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

.avatar-agent {
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  border: 1px solid var(--color-primary-border);
}

.avatar-user {
  background-color: #f1f5f9;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.avatar-skipped {
  background-color: #f8fafc;
  color: var(--color-text-muted);
}

.bubble-container {
  flex: 1;
  max-width: 90%;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.bubble-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
}

.sender-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.badge-role {
  font-size: 0.6875rem;
  color: var(--color-primary);
  background-color: var(--color-primary-light);
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
  font-weight: 500;
}

.badge-skipped {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  background-color: #f1f5f9;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
  font-weight: 500;
}

.timestamp {
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

.message-user .bubble-body {
  background-color: #f8fafc;
  border-color: var(--color-border-strong);
}

.body-skipped {
  background-color: #fafbfc !important;
  border-style: dashed;
}

.bubble-text {
  font-size: 0.9375rem;
  color: var(--color-text-primary);
  white-space: pre-line;
}

.body-skipped .bubble-text {
  color: var(--color-text-muted);
  font-style: italic;
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
</style>
