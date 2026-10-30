<script setup lang="ts">
import { computed } from 'vue'
import type { RepoSignals } from '@/types/signals'
import type { UnresolvedKnowledgeGap } from '@/types/advisor'
import type { BackendPipelineProgress } from '@/api/types'

const props = defineProps<{
  signals?: RepoSignals
  progress: BackendPipelineProgress | null
  knowledgeGaps: UnresolvedKnowledgeGap[]
  isMock?: boolean
}>()

/** Only facts the scanner actually produced: a row with no value is hidden,
 *  never filled with a placeholder. */
const contextRows = computed(() => {
  const s = props.signals
  if (!s) return []
  const rows: { label: string; value: string }[] = []
  const primary = s.languages?.[0]?.name
  if (s.totalSupportedFiles) rows.push({ label: 'Code files', value: String(s.totalSupportedFiles) })
  if (primary) rows.push({ label: 'Primary language', value: primary })
  if (s.stack?.frameworks?.length) rows.push({ label: 'Frameworks', value: s.stack.frameworks.join(', ') })
  if (s.quality?.sourceFilesCount) {
    rows.push({ label: 'Test files', value: `${s.quality.testFilesCount} of ${s.quality.sourceFilesCount} source files` })
  }
  if (s.cicd?.ciProvider) rows.push({ label: 'CI', value: s.cicd.ciProvider })
  return rows
})

const PHASE_TEXT: Record<BackendPipelineProgress['phase'], string> = {
  starting: 'Preparing the repository',
  specialist: 'Reviewing the repository',
  waiting_for_answer: 'Waiting for your answer',
  synthesizing: 'Writing the report',
  complete: 'Done',
  error: 'Stopped with an error'
}

const activity = computed(() => {
  const p = props.progress
  if (!p) return null
  const name =
    p.phase === 'synthesizing' ? 'Synthesizer' : p.phase === 'starting' ? 'Supervisor' : p.current_label || 'Specialist'
  return {
    name,
    initial: name.charAt(0).toUpperCase(),
    phaseText: PHASE_TEXT[p.phase],
    stepText: p.phase === 'specialist' || p.phase === 'waiting_for_answer' ? `Step ${p.step} of ${p.total_steps}` : '',
    percent: Math.round((p.completed_specialists / Math.max(p.total_steps, 1)) * 100),
    busy: p.phase === 'specialist' || p.phase === 'starting' || p.phase === 'synthesizing'
  }
})
</script>

<template>
  <aside class="topics-panel" aria-label="Diagnostic context and specialist activity">
    <!-- 1. Repository context: scanner facts only -->
    <div v-if="signals" class="card context-card">
      <h3 class="card-title">{{ signals.repoName }}</h3>
      <p v-if="isMock" class="repo-summary-text">Sample data</p>
      <div v-if="contextRows.length" class="meta-stats-grid">
        <div v-for="row in contextRows" :key="row.label" class="meta-stat-row">
          <span class="meta-label">{{ row.label }}</span>
          <span class="meta-val">{{ row.value }}</span>
        </div>
      </div>
    </div>

    <!-- 2. Specialist activity: only the agent working right now -->
    <div v-if="activity" class="card activity-card">
      <h3 class="card-title">Specialist activity</h3>
      <div class="specialist-box">
        <div class="specialist-row-top">
          <div class="specialist-row-left">
            <div class="specialist-avatar">{{ activity.initial }}</div>
            <div class="specialist-text">
              <span class="specialist-name">{{ activity.name }}</span>
              <span class="specialist-phase">
                <span v-if="activity.busy" class="pulse-dot" aria-hidden="true"></span>
                {{ activity.phaseText }}
              </span>
            </div>
          </div>
          <span v-if="activity.stepText" class="badge badge-step">{{ activity.stepText }}</span>
        </div>
        <div
          class="progress-track"
          role="progressbar"
          :aria-valuenow="activity.percent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`${progress?.completed_specialists} of ${progress?.total_steps} specialists done`"
        >
          <div class="progress-fill" :style="{ width: `${activity.percent}%` }"></div>
        </div>
        <span class="progress-caption">{{ progress?.completed_specialists }} of {{ progress?.total_steps }} specialists done</span>
      </div>
    </div>

    <!-- 3. Unresolved knowledge gaps (from the specialists' reports) -->
    <div v-if="knowledgeGaps.length" class="card gaps-card">
      <h3 class="card-title">Unresolved knowledge gaps</h3>
      <div class="gaps-list">
        <div v-for="gap in knowledgeGaps" :key="gap.id" class="gap-box">
          <strong class="gap-title">{{ gap.title }}</strong>
          <p class="gap-desc">{{ gap.description }}</p>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.topics-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card {
  padding: 1.25rem;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.card-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 0.75rem;
}

/* 1. Context Card */
.repo-summary-text {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: -0.5rem;
  margin-bottom: 0.75rem;
}

.meta-stats-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.meta-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  font-size: 0.8125rem;
}

.meta-label {
  color: var(--color-text-muted);
  white-space: nowrap;
}

.meta-val {
  font-weight: 600;
  color: var(--color-text-primary);
  text-align: right;
}

/* 2. Specialist Activity */
.specialist-box {
  background-color: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  padding: 0.75rem 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.specialist-row-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.specialist-row-left {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.specialist-avatar {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background-color: #f3e8ff;
  color: #7c3aed;
}

.specialist-text {
  display: flex;
  flex-direction: column;
}

.specialist-name {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.specialist-phase {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--color-primary);
  animation: pulse 1.2s ease-in-out infinite;
}

.badge-step {
  background-color: #ede9fe;
  color: #6d28d9;
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.progress-track {
  height: 4px;
  background-color: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
  width: 100%;
}

.progress-fill {
  height: 100%;
  background-color: var(--color-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-caption {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
}

/* 3. Unresolved Knowledge Gaps */
.gaps-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.gap-box {
  background-color: #fffdf5;
  border: 1px solid #fef08a;
  border-radius: 8px;
  padding: 0.625rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.gap-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #854d0e;
}

.gap-desc {
  font-size: 0.75rem;
  color: #713f12;
  line-height: 1.45;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.3;
  }
  50% {
    opacity: 1;
  }
}
</style>
