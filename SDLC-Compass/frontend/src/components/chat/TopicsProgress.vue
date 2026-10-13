<script setup lang="ts">
import type { TopicProgress } from '@/types/questions'
import type { RepoSignals } from '@/types/signals'

defineProps<{
  topics: TopicProgress[]
  signals?: RepoSignals
  answeredCount: number
  totalCount: number
  canGenerate: boolean
}>()

const emit = defineEmits<{
  (e: 'generate'): void
  (e: 'back'): void
}>()
</script>

<template>
  <aside class="topics-panel" aria-label="Topic clarification progress">
    <!-- 1. Repository Quick Context Card -->
    <div v-if="signals" class="card context-card">
      <div class="card-header">
        <h3 class="card-title">{{ signals.repoName }}</h3>
        <span class="badge badge-poc">PoC Context</span>
      </div>
      <p class="repo-summary-text">
        {{ signals.totalSupportedFiles }} code files · {{ signals.stack.frameworks.join(' + ') }} · {{ signals.quality.testFilesCount }} test files / {{ signals.quality.sourceFilesCount }} source files
      </p>

      <div class="meta-stats-grid">
        <div class="meta-stat-row">
          <span class="meta-label">Team method</span>
          <span class="meta-val">Scrum · 8 members</span>
        </div>
        <div class="meta-stat-row">
          <span class="meta-label">AI starting point</span>
          <span class="meta-val">Exploratory</span>
        </div>
        <div class="meta-stat-row">
          <span class="meta-label">Current tools</span>
          <span class="meta-val">Copilot pilot · ChatGPT</span>
        </div>
      </div>
    </div>

    <!-- 2. Topics Progress Card (Answered vs Pending) -->
    <div class="card topics-card">
      <div class="topics-card-header">
        <h3 class="card-title">Diagnostic topics</h3>
        <span class="badge badge-purple">{{ answeredCount }} of {{ totalCount }} answered</span>
      </div>
      <p class="topics-subtitle">
        Topics guide which SDLC phase recommendations will receive deeper justification.
      </p>

      <ul class="topic-list">
        <li
          v-for="topic in topics"
          :key="topic.id"
          class="topic-item"
          :class="`topic-status-${topic.status}`"
        >
          <!-- Status icon -->
          <div class="topic-icon-wrap" aria-hidden="true">
            <template v-if="topic.status === 'completed'">
              <svg class="check-icon" viewBox="0 0 16 16" fill="currentColor">
                <path
                  fill-rule="evenodd"
                  d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
                  clip-rule="evenodd"
                />
              </svg>
            </template>
            <template v-else-if="topic.status === 'current'">
              <div class="current-dot"></div>
            </template>
            <template v-else>
              <div class="pending-circle"></div>
            </template>
          </div>

          <div class="topic-info">
            <span class="topic-name">{{ topic.name }}</span>
            <span class="topic-status-label">
              {{ topic.status === 'completed' ? 'Answered' : topic.status === 'current' ? 'In progress' : 'Pending' }}
            </span>
          </div>
        </li>
      </ul>
    </div>

    <!-- 3. Specialist Activity Preview Card -->
    <div class="card activity-card">
      <h3 class="card-title">Specialist activity</h3>
      <div class="specialist-item">
        <div class="specialist-header">
          <span class="specialist-name">Requirements & Design</span>
          <span class="badge badge-info">Analyzing</span>
        </div>
        <p class="specialist-desc">
          Examining acceptance criteria coverage and design decision documentation.
        </p>
      </div>

      <div class="specialist-item">
        <div class="specialist-header">
          <span class="specialist-name">QA, CI/CD & Testing</span>
          <span class="badge badge-info">Analyzing</span>
        </div>
        <p class="specialist-desc">
          Mapping local test execution against CI pipeline coverage.
        </p>
      </div>
    </div>

    <!-- 4. Path to an evolving diagnostic Card -->
    <div class="card finish-card">
      <h3 class="card-title">Path to diagnostic</h3>
      <p class="finish-desc">
        Answer follow-up questions to ground the report. You can generate the diagnostic whenever ready.
      </p>

      <div class="finish-actions">
        <button
          type="button"
          class="btn-primary generate-btn"
          :disabled="!canGenerate"
          @click="emit('generate')"
        >
          <span>Generate diagnostic report</span>
          <svg class="btn-arrow" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path
              fill-rule="evenodd"
              d="M6.22 3.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06Z"
              clip-rule="evenodd"
            />
          </svg>
        </button>

        <button type="button" class="btn-ghost back-btn" @click="emit('back')">
          ← Back to signals review
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.topics-panel {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.card-title {
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

/* Context Card */
.context-card {
  padding: 1.5rem;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.repo-summary-text {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
  margin-bottom: 1rem;
}

.meta-stats-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-top: 1px solid var(--color-border-subtle);
  padding-top: 0.75rem;
}

.meta-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8125rem;
}

.meta-label {
  color: var(--color-text-muted);
}

.meta-val {
  color: var(--color-text-primary);
  font-weight: 500;
}

/* Topics Card */
.topics-card {
  padding: 1.5rem;
}

.topics-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.375rem;
}

.topics-subtitle {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  line-height: 1.4;
  margin-bottom: 1.25rem;
}

.topic-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.topic-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.875rem;
  border-radius: var(--radius-md);
  background-color: #fafbfc;
  border: 1px solid var(--color-border-subtle);
  transition: all 0.15s ease;
}

.topic-status-current {
  background-color: var(--color-primary-light);
  border-color: var(--color-primary-border);
}

.topic-status-completed {
  background-color: #f0fdf4;
  border-color: #bbf7d0;
}

.topic-icon-wrap {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.topic-status-completed .topic-icon-wrap {
  color: #16a34a;
}

.check-icon {
  width: 16px;
  height: 16px;
}

.current-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.pending-circle {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #cbd5e1;
}

.topic-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.topic-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.topic-status-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.topic-status-current .topic-status-label {
  color: var(--color-primary);
  font-weight: 600;
}

/* Specialist Activity Card */
.activity-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.specialist-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--color-border-subtle);
}

.specialist-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.specialist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.specialist-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.specialist-desc {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

/* Finish Card */
.finish-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.finish-desc {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

.finish-actions {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  margin-top: 0.5rem;
}

.generate-btn {
  width: 100%;
}

.btn-arrow {
  width: 16px;
  height: 16px;
}

.back-btn {
  font-size: 0.8125rem;
}
</style>
