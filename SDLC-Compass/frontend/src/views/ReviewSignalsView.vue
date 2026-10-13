<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import SignalCard from '@/components/signals/SignalCard.vue'
import SignalEditModal, { type EditableSignalCategory } from '@/components/signals/SignalEditModal.vue'
import type { RepoSignals } from '@/types/signals'

const router = useRouter()
const store = useSessionStore()

// Active editing state
const activeEditCategory = ref<EditableSignalCategory | null>(null)

onMounted(() => {
  store.ensureSampleSignals()
  store.setStep(2)
})

const signals = computed<RepoSignals>(() => {
  return store.repoSignals!
})
const isMock = computed(() => store.isMock)
const evidenceLabel = computed(() => isMock.value ? 'SAMPLE EVIDENCE' : 'EVIDENCE')

// Modal actions
function openEdit(category: EditableSignalCategory) {
  activeEditCategory.value = category
}

function closeEdit() {
  activeEditCategory.value = null
}

async function handleSaveEditedSignals(updated: RepoSignals) {
  await store.updateReviewedSignals(updated)
  closeEdit()
}

// Navigation
function goBack() {
  router.push('/')
}

async function handleContinue() {
  try {
    await store.confirmSignals()
    router.push('/questions')
  } catch {
    // Handled in store error state
  }
}
</script>

<template>
  <div v-if="signals" class="review-view container">
    <!-- Top Step Meta Header -->
    <div class="screen-meta">
      <span class="step-badge">TEAM DIAGNOSTIC / STEP 2 OF 5</span>
      <h1 class="page-title">Review the evidence, not assumptions</h1>
      <p class="page-subtitle">
        Confirm the extracted signals. Each card can be corrected before it informs your diagnostic.
      </p>
    </div>

    <!-- Repository Header Summary Banner -->
    <div class="card repo-summary-card">
      <div class="repo-summary-left">
        <div class="check-circle-icon" aria-hidden="true">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
              clip-rule="evenodd"
            />
          </svg>
        </div>

        <div class="repo-meta-text">
          <div class="repo-title-row">
            <h2 class="repo-name">{{ signals.repoName }}</h2>
            <span class="badge badge-success">Scan complete</span>
            <span v-if="isMock" class="badge badge-purple">Sample data</span>
          </div>
          <div class="repo-submeta">
            <template v-if="isMock">
              <span>sample/atlas-service</span>
              <span>·</span>
              <span>main</span>
              <span>·</span>
              <span>Illustrative commit {{ signals.commitHash || 'a8f2c10' }}</span>
            </template>
            <template v-else>
              <span v-if="signals.repoUrl">{{ signals.repoUrl }}</span>
              <template v-if="signals.commitHash">
                <span>·</span>
                <span>commit {{ signals.commitHash }}</span>
              </template>
            </template>
          </div>
        </div>
      </div>

      <div class="repo-summary-right">
        <span class="badge badge-success poc-eligible-tag">
          {{ signals.isEligiblePoC ? 'Eligible for PoC' : 'Scope Notice' }}
        </span>
        <span class="repo-scope-counts">
          {{ signals.totalSupportedFiles }} supported code files · {{ signals.excludedItemsCount }} excluded items
        </span>
      </div>
    </div>

    <!-- Signals Section Header -->
    <div class="section-heading-row">
      <h2 class="section-title">Repository signals</h2>
      <span class="section-note">
        <template v-if="isMock">Sample data · </template>6 editable signal groups · Estimates are not validated measurements
      </span>
    </div>

    <!-- 6 Signals Grid -->
    <div class="signals-grid">
      <!-- 1. Languages Card -->
      <SignalCard
        title="Languages"
        badge-text="High confidence · File extensions"
        badge-class="badge-purple"
        :sample-evidence="signals.languages.map((l) => `*.${l.name.toLowerCase().slice(0, 2)}`).join(' · ')"
        :evidence-label="evidenceLabel"
        @edit="openEdit('languages')"
      >
        <template #icon>
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M6.28 5.22a.75.75 0 0 1 0 1.06L2.56 10l3.72 3.72a.75.75 0 0 1-1.06 1.06L.97 10.53a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Zm7.44 0a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L17.44 10l-3.72-3.72a.75.75 0 0 1 0-1.06ZM11.377 2.011a.75.75 0 0 1 .612.867l-2.5 14.5a.75.75 0 0 1-1.478-.256l2.5-14.5a.75.75 0 0 1 .866-.611Z"
              clip-rule="evenodd"
            />
          </svg>
        </template>

        <div class="languages-list">
          <div
            v-for="lang in signals.languages"
            :key="lang.name"
            class="lang-item"
          >
            <div class="lang-label-row">
              <span class="lang-name">{{ lang.name }}</span>
              <span class="lang-stat">{{ lang.files }} files · {{ lang.percentage }}%</span>
            </div>
            <div class="progress-bar-track">
              <div
                class="progress-bar-fill"
                :style="{ width: `${lang.percentage}%` }"
              ></div>
            </div>
          </div>
        </div>

        <template #footnote>
          No Java detected. Manifests and config files support evidence but are not counted as code files.
        </template>
      </SignalCard>

      <!-- 2. Size & Structure Card -->
      <SignalCard
        title="Size & structure"
        badge-text="Mixed confidence · Counts + estimates"
        badge-class="badge-info"
        :sample-evidence="signals.size.evidenceSummary"
        :evidence-label="evidenceLabel"
        @edit="openEdit('size')"
      >
        <template #icon>
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M4.25 2A2.25 2.25 0 0 0 2 4.25v11.5A2.25 2.25 0 0 0 4.25 18h11.5A2.25 2.25 0 0 0 18 15.75V4.25A2.25 2.25 0 0 0 15.75 2H4.25Zm0 1.5h11.5c.414 0 .75.336.75.75v1.25H3.5V4.25c0-.414.336-.75.75-.75Zm12.25 3.5H3.5v8.5c0 .414.336.75.75.75h11.5a.75.75 0 0 0 .75-.75V7Z"
              clip-rule="evenodd"
            />
          </svg>
        </template>

        <div class="size-stats-row">
          <div class="stat-unit">
            <span class="stat-big-number">{{ signals.size.codeFiles }}</span>
            <span class="stat-label">Code files</span>
          </div>
          <div class="stat-unit">
            <span class="stat-big-number">~{{ signals.size.locEstimate.toLocaleString() }}</span>
            <span class="stat-label">LOC estimate</span>
          </div>
          <div class="stat-unit">
            <span class="stat-big-number">~{{ signals.size.moduleEstimate }}</span>
            <span class="stat-label">Module estimate</span>
          </div>
        </div>

        <div class="key-value-row">
          <span class="kv-key">Approx. complexity</span>
          <span class="kv-val">{{ signals.size.approxComplexity }} · Low confidence</span>
        </div>

        <template #footnote>
          LOC, module boundaries and complexity are illustrative estimates, not validated capabilities.
          Excludes dependencies, .git, binaries and generated files.
        </template>
      </SignalCard>

      <!-- 3. Stack & Tooling Card -->
      <SignalCard
        title="Stack & tooling"
        badge-text="High confidence · Dependency manifests"
        badge-class="badge-purple"
        :sample-evidence="signals.stack.sampleEvidence"
        :evidence-label="evidenceLabel"
        @edit="openEdit('stack')"
      >
        <template #icon>
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M10 1a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 10 1ZM5.05 3.05a.75.75 0 0 1 1.06 0l1.062 1.06a.75.75 0 0 1-1.06 1.062L5.05 4.11a.75.75 0 0 1 0-1.06Zm9.9 0a.75.75 0 0 1 0 1.06l-1.06 1.062a.75.75 0 1 1-1.062-1.06L13.89 3.05a.75.75 0 0 1 1.06 0ZM10 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"
              clip-rule="evenodd"
            />
          </svg>
        </template>

        <div class="tooling-rows">
          <div class="key-value-row">
            <span class="kv-key">Frameworks</span>
            <span class="kv-val strong">{{ signals.stack.frameworks.join(' · ') }}</span>
          </div>
          <div class="key-value-row">
            <span class="kv-key">Testing libraries</span>
            <span class="kv-val strong">{{ signals.stack.testingLibraries.join(' · ') }}</span>
          </div>
          <div class="key-value-row">
            <span class="kv-key">Build tools</span>
            <span class="kv-val strong">{{ signals.stack.buildTools.join(' · ') }}</span>
          </div>
        </div>

        <template #footnote>
          Dependencies indicate declared tooling, not that it is actively used or configured correctly.
        </template>
      </SignalCard>

      <!-- 4. CI/CD & Operations Card -->
      <SignalCard
        title="CI/CD & operations"
        badge-text="Medium confidence · Config inspection"
        badge-class="badge-info"
        :sample-evidence="signals.cicd.sampleEvidence"
        :evidence-label="evidenceLabel"
        @edit="openEdit('cicd')"
      >
        <template #icon>
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.451a.75.75 0 0 0 0-1.5H4.5a.75.75 0 0 0-.75.75v3.75a.75.75 0 0 0 1.5 0v-2.183l.443.443a7 7 0 0 0 11.89-3.238.75.75 0 0 0-1.27-.677ZM4.688 8.576a5.5 5.5 0 0 1 9.201-2.466l.312.311h-2.45a.75.75 0 0 0 0 1.5h3.75a.75.75 0 0 0 .75-.75V3.421a.75.75 0 0 0-1.5 0v2.183l-.443-.443a7 7 0 0 0-11.89 3.238.75.75 0 1 0 1.27.677Z"
              clip-rule="evenodd"
            />
          </svg>
        </template>

        <div class="tooling-rows">
          <div class="key-value-row">
            <span class="kv-key">CI/CD</span>
            <span class="kv-val strong">
              {{ signals.cicd.ciProvider }} · {{ signals.cicd.hasBuildJob ? 'Build job detected' : 'No job' }}
            </span>
          </div>
          <div class="key-value-row">
            <span class="kv-key">Containerisation</span>
            <span class="kv-val strong">{{ signals.cicd.containerization }}</span>
          </div>
          <div class="key-value-row">
            <span class="kv-key">Documentation</span>
            <span class="kv-val strong">{{ signals.cicd.documentation }}</span>
          </div>
        </div>

        <template #footnote>
          No test or deployment job detected. Workflow configuration was reviewed; no pipeline was executed.
        </template>
      </SignalCard>

      <!-- 5. Quality Indicators Card -->
      <SignalCard
        title="Quality indicators"
        badge-text="Estimated proxy · Not executed coverage"
        badge-class="badge-purple"
        :sample-evidence="signals.quality.sampleEvidence"
        :evidence-label="evidenceLabel"
        @edit="openEdit('quality')"
      >
        <template #icon>
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M9 3.5a1.5 1.5 0 0 1 1.5-1.5h1A1.5 1.5 0 0 1 13 3.5v.75A6.5 6.5 0 0 1 17.5 10v4.75a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 14.75V10A6.5 6.5 0 0 1 9 4.25V3.5ZM10.5 5a5 5 0 0 0-4.5 5v4.75c0 .414.336.75.75.75h8.5a.75.75 0 0 0 .75-.75V10a5 5 0 0 0-4.5-5h-1Z"
              clip-rule="evenodd"
            />
          </svg>
        </template>

        <div class="quality-stat-block">
          <div class="stat-unit">
            <span class="stat-big-number">{{ signals.quality.testToCodeRatio }}%</span>
            <span class="stat-label">Test-to-code file ratio</span>
          </div>
        </div>

        <div class="tooling-rows">
          <div class="key-value-row">
            <span class="kv-key">Executed coverage</span>
            <span class="kv-val strong">{{ signals.quality.executedCoverage }}</span>
          </div>
          <div class="key-value-row">
            <span class="kv-key">Quality gate</span>
            <span class="kv-val strong">{{ signals.quality.qualityGateStatus }}</span>
          </div>
        </div>

        <template #footnote>
          File ratio is a proxy for test presence, not coverage or test quality. No tests or static analysis were run.
        </template>
      </SignalCard>

      <!-- 6. Warnings & Missing Signals Card -->
      <SignalCard
        title="Warnings & missing signals"
        badge-text="Needs confirmation · Low confidence"
        badge-class="badge-warning"
        :sample-evidence="signals.warnings[0]?.sampleEvidence || '.github/workflows/build.yml'"
        :evidence-label="evidenceLabel"
        @edit="openEdit('warnings')"
      >
        <template #icon>
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fill-rule="evenodd"
              d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 5Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
              clip-rule="evenodd"
            />
          </svg>
        </template>

        <div class="warnings-list">
          <div
            v-for="warning in signals.warnings"
            :key="warning.id"
            class="warning-item"
          >
            <strong class="warning-title">{{ warning.title }}</strong>
            <p class="warning-desc">{{ warning.description }}</p>
          </div>
        </div>
      </SignalCard>
    </div>

    <!-- Need to change the scope banner -->
    <div class="scope-notice-banner card">
      <div class="notice-icon" aria-hidden="true">
        <svg viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
            clip-rule="evenodd"
          />
        </svg>
      </div>
      <div class="notice-text">
        <strong class="notice-title">Need to change the scope?</strong>
        <p class="notice-body">
          For unsupported or oversized content, analyse a supported subset, continue with a scope warning, or cancel.
          This sample is within the PoC scope.
        </p>
      </div>
    </div>

    <!-- Bottom Navigation Actions -->
    <div class="bottom-action-bar">
      <button type="button" class="btn-secondary back-btn" @click="goBack">
        <svg class="nav-arrow" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M9.78 3.22a.75.75 0 0 1 0 1.06L6.06 8l3.72 3.72a.75.75 0 1 1-1.06 1.06L4.47 8.53a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z"
            clip-rule="evenodd"
          />
        </svg>
        <span>Back</span>
      </button>

      <span class="action-caption">Confirmed signals feed the diagnostic.</span>

      <button
        type="button"
        class="btn-primary continue-btn"
        @click="handleContinue"
      >
        <span>Confirm & add team context</span>
        <svg class="nav-arrow" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M6.22 3.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06Z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
    </div>

    <!-- Modal for editing active signal category -->
    <SignalEditModal
      v-if="activeEditCategory"
      :category="activeEditCategory"
      :signals="signals"
      @save="handleSaveEditedSignals"
      @close="closeEdit"
    />
  </div>
</template>

<style scoped>
.review-view {
  padding-top: 2.25rem;
  padding-bottom: 4rem;
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
  font-size: 1.0625rem;
  color: var(--color-text-secondary);
}

/* Summary Card */
.repo-summary-card {
  padding: 1.25rem 1.75rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  margin-bottom: 2.5rem;
  background-color: var(--color-surface);
}

.repo-summary-left {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.check-circle-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.check-circle-icon svg {
  width: 20px;
  height: 20px;
}

.repo-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.repo-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.repo-submeta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin-top: 0.25rem;
}

.repo-summary-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.375rem;
}

.poc-eligible-tag {
  align-self: flex-end;
}

.repo-scope-counts {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}

/* Section Header */
.section-heading-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.section-note {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

/* 6 Grid Cards */
.signals-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;
}

/* Languages Card Content */
.languages-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.lang-label-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 0.875rem;
  margin-bottom: 0.375rem;
}

.lang-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.lang-stat {
  color: var(--color-text-muted);
  font-size: 0.8125rem;
}

.progress-bar-track {
  width: 100%;
  height: 6px;
  background-color: #f1f5f9;
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background-color: var(--color-primary);
  border-radius: var(--radius-full);
}

/* Size Card Content */
.size-stats-row {
  display: flex;
  align-items: center;
  gap: 2rem;
  margin-bottom: 0.75rem;
}

.stat-unit {
  display: flex;
  flex-direction: column;
}

.stat-big-number {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-text-primary);
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.25rem;
}

/* Key Value Rows */
.tooling-rows {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.key-value-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 0.875rem;
  padding: 0.25rem 0;
}

.kv-key {
  color: var(--color-text-muted);
}

.kv-val {
  color: var(--color-text-primary);
}

.kv-val.strong {
  font-weight: 600;
}

/* Quality Stat Block */
.quality-stat-block {
  margin-bottom: 0.5rem;
}

/* Warnings List */
.warnings-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.warning-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.warning-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.warning-desc {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

/* Scope Notice Banner */
.scope-notice-banner {
  background-color: #f5f3ff;
  border-color: #ddd6fe;
  padding: 1.25rem 1.5rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 2.5rem;
}

.notice-icon {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
  flex-shrink: 0;
  margin-top: 2px;
}

.notice-icon svg {
  width: 100%;
  height: 100%;
}

.notice-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.notice-title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--color-primary);
}

.notice-body {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

/* Bottom Action Bar */
.bottom-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
}

.action-caption {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.back-btn {
  padding-left: 1.25rem;
  padding-right: 1.25rem;
}

.continue-btn {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
}

.nav-arrow {
  width: 16px;
  height: 16px;
}

/* Responsive */
@media (max-width: 900px) {
  .signals-grid {
    grid-template-columns: 1fr;
  }

  .repo-summary-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .repo-summary-right {
    align-items: flex-start;
  }

  .poc-eligible-tag {
    align-self: flex-start;
  }
}

@media (max-width: 640px) {
  .page-title {
    font-size: 1.75rem;
  }

  .bottom-action-bar {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .continue-btn,
  .back-btn {
    width: 100%;
  }

  .action-caption {
    text-align: center;
  }
}
</style>
