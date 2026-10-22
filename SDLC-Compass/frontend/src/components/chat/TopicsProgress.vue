<script setup lang="ts">
import { computed } from 'vue'
import type { RepoSignals } from '@/types/signals'
import type { SpecialistActivity, UnresolvedKnowledgeGap } from '@/types/advisor'

const props = defineProps<{
  signals?: RepoSignals
  activeTab: string
  specialists: SpecialistActivity[]
  knowledgeGaps: UnresolvedKnowledgeGap[]
  isMock?: boolean
}>()

function getAvatarLetter(title: string): string {
  if (title.includes('Requirements')) return 'R'
  if (title.includes('Code')) return 'C'
  if (title.includes('QA') || title.includes('Testing')) return 'Q'
  if (title.includes('DevOps') || title.includes('Monitoring')) return 'D'
  return title.charAt(0) || 'A'
}

function getAvatarClass(title: string): string {
  const l = getAvatarLetter(title)
  if (l === 'R' || l === 'Q') return 'avatar-purple'
  return 'avatar-indigo'
}

const selectedSpecialist = computed<SpecialistActivity | undefined>(() => {
  return props.specialists.find((s) => {
    if (props.activeTab === 'requirements') return s.phase.includes('Requirements') || s.title.includes('Requirements')
    if (props.activeTab === 'code') return s.phase.includes('Code') || s.title.includes('Code')
    if (props.activeTab === 'testing') return s.phase.includes('QA') || s.phase.includes('Testing') || s.title.includes('QA')
    if (props.activeTab === 'devops') return s.phase.includes('DevOps') || s.title.includes('DevOps')
    return false
  })
})
</script>

<template>
  <aside class="topics-panel" aria-label="Diagnostic context and specialist activity">
    <!-- 1. Repository Quick Context Card -->
    <div class="card context-card">
      <div class="context-header">
        <h3 class="card-title">{{ signals?.repoName || 'Atlas Service' }}</h3>
      </div>
      <p class="repo-summary-text">
        <template v-if="isMock">Sample data · </template>{{ signals?.totalSupportedFiles || 48 }} code files · {{ signals?.stack?.frameworks?.join(' + ') || 'FastAPI + React' }} · {{ signals?.quality?.testFilesCount || 6 }} test files / {{ signals?.quality?.sourceFilesCount || 42 }} source files
      </p>

      <div class="meta-stats-grid">
        <div class="meta-stat-row">
          <span class="meta-label">Repository</span>
          <span class="meta-val">Reviewed · 6 signal groups</span>
        </div>
        <div class="meta-stat-row">
          <span class="meta-label">Scope</span>
          <span class="meta-val">{{ signals?.totalSupportedFiles || 48 }} code files · PoC eligible</span>
        </div>
        <div class="meta-stat-row">
          <span class="meta-label">Team</span>
          <span class="meta-val">Scrum · 8 members</span>
        </div>
        <div class="meta-stat-row">
          <span class="meta-label">AI starting point</span>
          <span class="meta-val">Exploratory</span>
        </div>
        <div class="meta-stat-row">
          <span class="meta-label">Pain points</span>
          <span class="meta-val">7 selected</span>
        </div>
        <div class="meta-stat-row">
          <span class="meta-label">Current tools</span>
          <span class="meta-val">Copilot pilot · ChatGPT</span>
        </div>
      </div>
    </div>

    <!-- 2. Specialist Activity Card -->
    <div class="card activity-card">
      <h3 class="card-title">Specialist activity</h3>

      <!-- Supervisor Tab View: All 4 specialists with avatar, name, analyzing badge, capacity %, and progress bar -->
      <div v-if="activeTab === 'supervisor'" class="supervisor-specialists-list">
        <div
          v-for="spec in specialists"
          :key="spec.id"
          class="specialist-box"
        >
          <div class="specialist-row-top">
            <div class="specialist-row-left">
              <div class="specialist-avatar" :class="getAvatarClass(spec.title)">
                {{ getAvatarLetter(spec.title) }}
              </div>
              <span class="specialist-name">{{ spec.title }}</span>
            </div>
            <div class="specialist-row-right">
              <span class="badge badge-analyzing">Analyzing</span>
              <span class="badge badge-capacity">{{ spec.capacityPercent ?? 50 }}%</span>
            </div>
          </div>
          <div
            class="progress-track"
            role="progressbar"
            :aria-valuenow="spec.capacityPercent ?? 50"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div class="progress-fill" :style="{ width: `${spec.capacityPercent ?? 50}%` }"></div>
          </div>
        </div>
      </div>

      <!-- Specialist Tab View: Selected specialist with description and evidence chips -->
      <div v-else-if="selectedSpecialist" class="specialist-detail-box">
        <div class="specialist-row-top">
          <div class="specialist-row-left">
            <div class="specialist-avatar" :class="getAvatarClass(selectedSpecialist.title)">
              {{ getAvatarLetter(selectedSpecialist.title) }}
            </div>
            <span class="specialist-name">{{ selectedSpecialist.title }}</span>
          </div>
          <span class="badge badge-analyzing">Analyzing</span>
        </div>
        <p class="specialist-description">{{ selectedSpecialist.description }}</p>
        <div v-if="selectedSpecialist.evidenceTokens && selectedSpecialist.evidenceTokens.length" class="evidence-chips-list">
          <span
            v-for="token in selectedSpecialist.evidenceTokens"
            :key="token"
            class="evidence-token-chip"
          >
            {{ token }}
          </span>
        </div>
      </div>
    </div>

    <!-- 3. Unresolved Knowledge Gaps Card -->
    <div class="card gaps-card">
      <h3 class="card-title">Unresolved knowledge gaps</h3>

      <div class="gaps-list">
        <div
          v-for="gap in knowledgeGaps"
          :key="gap.id"
          class="gap-box"
        >
          <div class="gap-top">
            <strong class="gap-title">{{ gap.title }}</strong>
            <span class="badge badge-gap-open">Open</span>
          </div>
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
  gap: 1.25rem;
}

.card {
  padding: 1.5rem;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

/* 1. Context Card */
.repo-summary-text {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  line-height: 1.45;
  margin-top: 0.25rem;
  margin-bottom: 1.125rem;
}

.meta-stats-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-top: 1px solid var(--color-border-subtle);
  padding-top: 0.875rem;
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
  font-weight: 600;
  color: var(--color-text-primary);
  text-align: right;
}

/* 2. Specialist Activity */
.activity-card {
  display: flex;
  flex-direction: column;
}

.activity-card .card-title {
  margin-bottom: 1rem;
}

.supervisor-specialists-list {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

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
  width: 26px;
  height: 26px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-purple {
  background-color: #f3e8ff;
  color: #7c3aed;
}

.avatar-indigo {
  background-color: #ede9fe;
  color: #6366f1;
}

.specialist-name {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.specialist-row-right {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.badge-analyzing {
  background-color: #f3e8ff;
  color: #7c3aed;
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
}

.badge-capacity {
  background-color: #ede9fe;
  color: #6d28d9;
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
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

/* Specialist Detail Mode (Tabs 2-5) */
.specialist-detail-box {
  background-color: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.specialist-description {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.evidence-chips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.evidence-token-chip {
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

/* 3. Unresolved Knowledge Gaps */
.gaps-card {
  display: flex;
  flex-direction: column;
}

.gaps-card .card-title {
  margin-bottom: 1rem;
}

.gaps-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.gap-box {
  background-color: #fffdf5;
  border: 1px solid #fef08a;
  border-radius: 8px;
  padding: 0.875rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.gap-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.gap-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #854d0e;
}

.badge-gap-open {
  background-color: #ffffff;
  border: 1px solid #fde68a;
  color: #a16207;
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-full);
}

.gap-desc {
  font-size: 0.8125rem;
  color: #713f12;
  line-height: 1.45;
}
</style>
