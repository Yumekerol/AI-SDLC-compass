<script setup lang="ts">
import type { AdvisorContext } from '@/types/advisor'
import type { DiagnosticReport } from '@/types/diagnostic'

defineProps<{
  context: AdvisorContext
  diagnosticReport?: DiagnosticReport | null
}>()

const emit = defineEmits<{
  (e: 'back-to-report'): void
}>()
</script>

<template>
  <aside class="advisor-context-sidebar" aria-label="Loaded context and current priorities">
    <!-- 1. Back to Report Navigation Action -->
    <div class="sidebar-top-nav">
      <button
        type="button"
        class="btn-secondary back-report-btn"
        @click="emit('back-to-report')"
      >
        <svg class="nav-arrow" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M9.78 3.22a.75.75 0 0 1 0 1.06L6.06 8l3.72 3.72a.75.75 0 1 1-1.06 1.06L4.47 8.53a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z"
            clip-rule="evenodd"
          />
        </svg>
        <span>Back to Diagnostic Report</span>
      </button>
    </div>

    <!-- 2. Repository & Team Context Card -->
    <div class="card context-overview-card">
      <div class="card-title-row">
        <h3 class="panel-card-title">{{ context.repoName }}</h3>
        <span class="badge badge-success">PoC Eligible</span>
      </div>
      <p class="summary-text">{{ context.summaryStats }}</p>

      <div class="context-attributes-list">
        <div class="attr-row">
          <span class="attr-key">Repository</span>
          <span class="attr-val">Reviewed · 6 signal groups</span>
        </div>
        <div class="attr-row">
          <span class="attr-key">Scope</span>
          <span class="attr-val">48 code files · Eligible</span>
        </div>
        <div class="attr-row">
          <span class="attr-key">Team</span>
          <span class="attr-val">{{ context.teamMethodology }}</span>
        </div>
        <div class="attr-row">
          <span class="attr-key">AI starting point</span>
          <span class="attr-val">{{ context.aiStartingPoint }}</span>
        </div>
        <div class="attr-row">
          <span class="attr-key">Pain points</span>
          <span class="attr-val">{{ context.painPointsCount }} selected</span>
        </div>
        <div class="attr-row">
          <span class="attr-key">Current tools</span>
          <span class="attr-val">{{ context.currentTools.join(' · ') }}</span>
        </div>
      </div>
    </div>

    <!-- 3. Current Priorities Card -->
    <div class="card priorities-card">
      <div class="card-title-row">
        <h3 class="panel-card-title">Current priorities</h3>
        <span class="badge badge-purple">6 phases</span>
      </div>
      <p class="priorities-sub">
        Priorities synthesized from evidence. You can challenge or adapt them in chat.
      </p>

      <ul class="priorities-list">
        <li class="priority-item priority-high">
          <div class="item-left">
            <span class="phase-bullet bullet-high" aria-hidden="true">●</span>
            <span class="phase-name">Testing</span>
          </div>
          <div class="item-right">
            <span class="badge badge-purple">High priority</span>
          </div>
        </li>
        <li class="priority-item priority-high">
          <div class="item-left">
            <span class="phase-bullet bullet-high" aria-hidden="true">●</span>
            <span class="phase-name">Requirements</span>
          </div>
          <div class="item-right">
            <span class="badge badge-success">Quick win</span>
            <span class="badge badge-purple">High</span>
          </div>
        </li>
        <li class="priority-item priority-high">
          <div class="item-left">
            <span class="phase-bullet bullet-high" aria-hidden="true">●</span>
            <span class="phase-name">Deployment</span>
          </div>
          <div class="item-right">
            <span class="badge badge-purple">High priority</span>
          </div>
        </li>
        <li class="priority-item priority-med">
          <div class="item-left">
            <span class="phase-bullet bullet-med" aria-hidden="true">●</span>
            <span class="phase-name">Design</span>
          </div>
          <div class="item-right">
            <span class="badge badge-success">Quick win</span>
            <span class="badge badge-info">Medium</span>
          </div>
        </li>
        <li class="priority-item priority-med">
          <div class="item-left">
            <span class="phase-bullet bullet-med" aria-hidden="true">●</span>
            <span class="phase-name">Development</span>
          </div>
          <div class="item-right">
            <span class="badge badge-info">Medium</span>
          </div>
        </li>
        <li class="priority-item priority-low">
          <div class="item-left">
            <span class="phase-bullet bullet-low" aria-hidden="true">●</span>
            <span class="phase-name">Monitoring</span>
          </div>
          <div class="item-right">
            <span class="badge badge-poc">Low</span>
          </div>
        </li>
      </ul>
    </div>

    <!-- 4. Unresolved Knowledge Gaps -->
    <div class="card gaps-card">
      <div class="card-title-row">
        <h3 class="panel-card-title">Unresolved knowledge gaps</h3>
        <span class="badge badge-warning">{{ context.unresolvedGaps.length }} open</span>
      </div>

      <div class="gaps-list">
        <div
          v-for="gap in context.unresolvedGaps"
          :key="gap.id"
          class="gap-box"
        >
          <div class="gap-top">
            <strong class="gap-title">{{ gap.title }}</strong>
            <span class="badge badge-warning">Open</span>
          </div>
          <p class="gap-desc">{{ gap.description }}</p>
        </div>
      </div>
    </div>

    <!-- 5. Specialist Activity Status -->
    <div class="card specialists-card">
      <h3 class="panel-card-title">Specialist activity</h3>
      <div class="specialist-rows">
        <div
          v-for="spec in context.specialists"
          :key="spec.id"
          class="spec-row"
        >
          <div class="spec-top">
            <span class="spec-name">{{ spec.title }}</span>
            <span class="badge badge-info">{{ spec.status }}</span>
          </div>
          <div class="spec-tokens">
            <span
              v-for="(tok, idx) in spec.evidenceTokens"
              :key="idx"
              class="token-pill"
            >
              {{ tok }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.advisor-context-sidebar {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.sidebar-top-nav {
  margin-bottom: -0.25rem;
}

.back-report-btn {
  width: 100%;
  justify-content: center;
  font-size: 0.875rem;
}

.nav-arrow {
  width: 16px;
  height: 16px;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.panel-card-title {
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

/* Context Overview Card */
.context-overview-card {
  padding: 1.5rem;
}

.summary-text {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
  margin-bottom: 1rem;
}

.context-attributes-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-top: 1px solid var(--color-border-subtle);
  padding-top: 0.75rem;
}

.attr-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8125rem;
}

.attr-key {
  color: var(--color-text-muted);
}

.attr-val {
  color: var(--color-text-primary);
  font-weight: 500;
  text-align: right;
}

/* Priorities Card */
.priorities-card {
  padding: 1.5rem;
}

.priorities-sub {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  line-height: 1.4;
  margin-bottom: 1rem;
}

.priorities-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.priority-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background-color: #fafbfc;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
}

.item-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.item-right {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.phase-bullet {
  font-size: 0.875rem;
}

.bullet-high {
  color: #7c3aed;
}

.bullet-med {
  color: #2563eb;
}

.bullet-low {
  color: #94a3b8;
}

.phase-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

/* Gaps Card */
.gaps-card {
  padding: 1.5rem;
}

.gaps-list {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  margin-top: 0.75rem;
}

.gap-box {
  background-color: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: var(--radius-md);
  padding: 0.875rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.gap-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.gap-title {
  font-size: 0.875rem;
  color: #92400e;
}

.gap-desc {
  font-size: 0.8125rem;
  color: #78350f;
  line-height: 1.4;
}

/* Specialists Card */
.specialists-card {
  padding: 1.5rem;
}

.specialist-rows {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 0.75rem;
}

.spec-row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--color-border-subtle);
}

.spec-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.spec-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.spec-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.spec-tokens {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.token-pill {
  font-size: 0.6875rem;
  background-color: #f1f5f9;
  color: #475569;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
}
</style>
