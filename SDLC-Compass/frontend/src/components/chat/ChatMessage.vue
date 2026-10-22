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
        <span v-if="roleBadge" class="meta-subtitle">
          {{ timestamp ? `${timestamp} · ` : '' }}{{ roleBadge }}
        </span>
        <span v-else-if="timestamp" class="meta-subtitle">{{ timestamp }}</span>
        <span v-if="isSkipped" class="badge-skipped">Skipped</span>
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
  margin-bottom: 0.75rem;
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
  background-color: var(--color-primary);
  color: #ffffff;
  border: 1px solid var(--color-primary);
}

.avatar-skipped {
  background-color: #f8fafc;
  color: var(--color-text-muted);
}

.bubble-container {
  flex: 1;
  max-width: 95%;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.bubble-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  padding-left: 0.25rem;
}

.sender-name {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: 0.875rem;
}

.meta-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 400;
}

.badge-skipped {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  background-color: #f1f5f9;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
  font-weight: 500;
}

.bubble-body {
  padding: 0.875rem 1.125rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background-color: var(--color-surface);
  box-shadow: var(--shadow-sm);
  line-height: 1.5;
}

.message-user .bubble-body {
  background-color: #faf5ff;
  border: 1.5px solid #c084fc;
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
