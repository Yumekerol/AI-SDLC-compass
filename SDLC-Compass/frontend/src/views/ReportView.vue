<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import * as api from '@/api'
import type { DiagnosticReport, SdlcPhase } from '@/types/diagnostic'
import ExecutiveSummary from '@/components/report/ExecutiveSummary.vue'
import PhaseCard from '@/components/report/PhaseCard.vue'
import ScopeLimitations from '@/components/report/ScopeLimitations.vue'
import { mockDiagnosticReport } from '@/mocks'

const router = useRouter()
const store = useSessionStore()

const exportNotice = ref<string>('')
const isExporting = ref<boolean>(false)

onMounted(async () => {
  store.ensureSampleSignals()
  store.setStep(4)

  if (!store.diagnostic) {
    store.diagnostic = JSON.parse(JSON.stringify(mockDiagnosticReport))
  }
})

const report = computed<DiagnosticReport>(() => {
  return store.diagnostic || mockDiagnosticReport
})
const isMock = computed(() => store.isMock)

const orderedPhases = computed<{ key: SdlcPhase; title: string }[]>(() => {
  if (
    report.value.phases['requirements_design'] ||
    report.value.phases['code_refactoring'] ||
    report.value.phases['qa_testing'] ||
    report.value.phases['devops_monitoring']
  ) {
    return [
      { key: 'requirements_design', title: 'Requirements & design' },
      { key: 'code_refactoring', title: 'Development' },
      { key: 'qa_testing', title: 'Testing' },
      { key: 'devops_monitoring', title: 'Deployment & monitoring' }
    ]
  }
  return [
    { key: 'requirements', title: 'Requirements' },
    { key: 'design', title: 'Design' },
    { key: 'development', title: 'Development' },
    { key: 'testing', title: 'Testing' },
    { key: 'deployment', title: 'Deployment' },
    { key: 'monitoring', title: 'Monitoring' }
  ]
})

function getRecommendationForPhase(key: string): any {
  const section = report.value.phases[key]
  if (section && section.recommendations && section.recommendations.length > 0) {
    return section.recommendations[0]
  }
  return {
    id: `rec-${key}-fallback`,
    phase: key,
    title: 'Establish AI Guardrails & Verification',
    priority: 'medium',
    effort: '1 sprint',
    expectedImpact: 'Foundational impact',
    justification: 'Assessment completed across available repository evidence.',
    examplePractice: 'Establish peer reviews and verifiable criteria before adopting autonomous tools.',
    quickWin: false
  }
}

// Actions
async function handleRegenerate() {
  await store.regenerateReport()
}

function handleAskAdvisor() {
  store.setStep(5)
  router.push('/advisor')
}

async function handleExportPdf() {
  isExporting.value = true
  exportNotice.value = ''
  try {
    const res = await api.exportPdfReport(store.sessionId || undefined)
    exportNotice.value = res.isPdf
      ? `Report successfully downloaded as PDF: ${res.filename}`
      : `Report downloaded as HTML deliverable: ${res.filename} (PDF renderer not available on host)`
    setTimeout(() => {
      exportNotice.value = ''
    }, 6000)
  } catch (err: unknown) {
    const anyErr = err as { message?: string }
    exportNotice.value = anyErr.message || 'Report download failed. Please retry.'
  } finally {
    isExporting.value = false
  }
}

function goBackToQuestions() {
  store.setStep(3)
  router.push('/questions')
}
</script>

<template>
  <div v-if="report" class="report-view container">
    <!-- Top Step Meta Header with Action Buttons -->
    <div class="report-header-row">
      <div class="screen-meta">
        <span class="step-badge">TEAM DIAGNOSTIC / STEP 4 OF 5</span>
        <h1 class="page-title">{{ report.repoName }} diagnostic workspace</h1>
        <p class="page-subtitle">
          The diagnostic is not final. Keep the conversation open, question the project, edit the report,
          and export a static PDF snapshot of the selected version.
        </p>
      </div>

      <!-- Header Action Buttons -->
      <div class="header-actions">
        <button
          type="button"
          class="btn-secondary"
          :disabled="store.isLoading"
          @click="handleRegenerate"
        >
          <svg class="action-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path
              fill-rule="evenodd"
              d="M13.836 2.477a.75.75 0 0 1 .75.75v3.182a.75.75 0 0 1-.75.75h-3.182a.75.75 0 0 1 0-1.5h1.861a5.5 5.5 0 1 0 1.025 5.09.75.75 0 0 1 1.439.426 7 7 0 1 1-1.328-6.448h1.435a.75.75 0 0 1 .75-.75Z"
              clip-rule="evenodd"
            />
          </svg>
          <span>Regenerate</span>
        </button>

        <button
          type="button"
          class="btn-secondary"
          :disabled="isExporting"
          @click="handleExportPdf"
        >
          <svg class="action-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path
              d="M3.5 2a.5.5 0 0 0-.5.5v11a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5V7.707a.5.5 0 0 0-.146-.354l-4.708-4.707A.5.5 0 0 0 8.293 2.5H3.5Zm5 1.5v3.5a.5.5 0 0 0 .5.5H12l-3.5-4Z"
            />
          </svg>
          <span>{{ isExporting ? 'Exporting...' : 'Export PDF' }}</span>
        </button>

        <button
          type="button"
          class="btn-primary"
          @click="handleAskAdvisor"
        >
          <svg class="action-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path
              d="M2 3.5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-3.5L5.2 13.7A.5.5 0 0 1 4.5 13.3V11.5H4a2 2 0 0 1-2-2v-6Z"
            />
          </svg>
          <span>Ask the advisor</span>
        </button>
      </div>
    </div>

    <!-- Export Toast Notice -->
    <div v-if="exportNotice" class="export-toast card" role="status" aria-live="polite">
      <svg class="toast-check-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
        <path
          fill-rule="evenodd"
          d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
          clip-rule="evenodd"
        />
      </svg>
      <span>{{ exportNotice }}</span>
    </div>

    <!-- 1. Executive Summary Dark Banner -->
    <ExecutiveSummary
      :headline="report.headline"
      :summary="report.executiveSummary"
      :high-priority-count="report.metrics.highPriorityCount"
      :quick-wins-count="report.metrics.quickWinsCount"
      :phases-covered-count="report.metrics.phasesCoveredCount"
      :is-mock="isMock"
    />

    <!-- 2. Project & Team Profile Snapshot -->
    <div class="card profile-snapshot-card">
      <div class="profile-card-header">
        <h2 class="profile-card-title">Project & team profile</h2>
        <span class="profile-subtitle">
          <template v-if="isMock">Sample data · </template>Reviewed repository signals + self-declared team context
        </span>
      </div>

      <div class="profile-four-grid">
        <div class="profile-col">
          <span class="col-heading">REPOSITORY</span>
          <strong class="col-value">48 code files</strong>
          <p class="col-detail">{{ report.projectProfile.codeFilesSummary }}</p>
        </div>

        <div class="profile-col">
          <span class="col-heading">TEAM</span>
          <strong class="col-value">8 members · Scrum</strong>
          <p class="col-detail">{{ report.projectProfile.teamSummary }}</p>
        </div>

        <div class="profile-col">
          <span class="col-heading">AI MATURITY</span>
          <strong class="col-value">Exploratory</strong>
          <p class="col-detail">{{ report.projectProfile.aiMaturitySummary }}</p>
        </div>

        <div class="profile-col">
          <span class="col-heading">QUALITY & CONFIDENCE</span>
          <strong class="col-value">14.3% file-ratio proxy</strong>
          <p class="col-detail">{{ report.projectProfile.qualitySummary }}</p>
        </div>
      </div>
    </div>

    <!-- 3. Evidence Gap Alert Banner -->
    <div v-if="report.evidenceGapAlert" class="evidence-alert-card card">
      <div class="alert-icon-wrap" aria-hidden="true">
        <svg viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 5Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
            clip-rule="evenodd"
          />
        </svg>
      </div>
      <div class="alert-text-group">
        <strong class="alert-title">{{ report.evidenceGapAlert.title }}</strong>
        <p class="alert-desc">{{ report.evidenceGapAlert.description }}</p>
      </div>
    </div>

    <!-- 4. Phase-by-Phase Recommendations Header -->
    <div class="recommendations-section-header">
      <div>
        <h2 class="section-title">Phase-by-phase recommendations</h2>
        <p class="section-sub">
          <template v-if="isMock">Sample data · </template>Qualitative expected outcomes, not guaranteed outcomes. Tool examples are illustrative.
        </p>
      </div>
      <span class="badge badge-poc">Human review required</span>
    </div>

    <!-- 5. 6 SDLC Phase Cards -->
    <div class="phase-cards-container">
      <PhaseCard
        v-for="phaseObj in orderedPhases"
        :key="phaseObj.key"
        :phase="phaseObj.key"
        :phase-title="phaseObj.title"
        :recommendation="getRecommendationForPhase(phaseObj.key)"
      />
    </div>

    <!-- 6. Scope & Limitations Section -->
    <ScopeLimitations
      :scope-items="report.scopeAndLimitations.currentPocScope"
      :roadmap-items="report.scopeAndLimitations.enterpriseRoadmap"
    />

    <!-- Bottom Sticky Navigation Actions -->
    <div class="bottom-action-bar">
      <button type="button" class="btn-secondary back-btn" @click="goBackToQuestions">
        <svg class="nav-arrow" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M9.78 3.22a.75.75 0 0 1 0 1.06L6.06 8l3.72 3.72a.75.75 0 1 1-1.06 1.06L4.47 8.53a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z"
            clip-rule="evenodd"
          />
        </svg>
        <span>Back to team context</span>
      </button>

      <span class="action-caption">
        Use the diagnostic to guide a team discussion, not replace delivery judgement.
      </span>

      <div class="bottom-action-buttons">
        <button
          type="button"
          class="btn-secondary"
          :disabled="isExporting"
          @click="handleExportPdf"
        >
          Export PDF
        </button>
        <button
          type="button"
          class="btn-primary"
          @click="handleAskAdvisor"
        >
          Ask the advisor →
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.report-view {
  padding-top: 2.25rem;
  padding-bottom: 4rem;
}

.report-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.screen-meta {
  max-width: 680px;
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.action-icon {
  width: 15px;
  height: 15px;
}

/* Export Toast Notice */
.export-toast {
  background-color: #ecfdf5;
  border-color: #a7f3d0;
  color: #065f46;
  padding: 0.875rem 1.25rem;
  border-radius: var(--radius-md);
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  animation: slideDown 0.2s ease-out;
}

.toast-check-icon {
  width: 18px;
  height: 18px;
}

/* Profile Snapshot Card */
.profile-snapshot-card {
  padding: 1.5rem 1.75rem;
  margin-bottom: 1.5rem;
}

.profile-card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--color-border-subtle);
}

.profile-card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.profile-subtitle {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.profile-four-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
}

.profile-col {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.col-heading {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.col-value {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.col-detail {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

/* Evidence Gap Alert */
.evidence-alert-card {
  background-color: #fffbeb;
  border-color: #fde68a;
  padding: 1.25rem 1.5rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 2.25rem;
}

.alert-icon-wrap {
  width: 22px;
  height: 22px;
  color: #b45309;
  flex-shrink: 0;
  margin-top: 2px;
}

.alert-icon-wrap svg {
  width: 100%;
  height: 100%;
}

.alert-text-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.alert-title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: #92400e;
}

.alert-desc {
  font-size: 0.8125rem;
  color: #78350f;
  line-height: 1.45;
}

/* Phase Header */
.recommendations-section-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.section-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.section-sub {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin-top: 0.25rem;
}

.phase-cards-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.bottom-action-buttons {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.nav-arrow {
  width: 16px;
  height: 16px;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 960px) {
  .report-header-row {
    flex-direction: column;
  }

  .profile-four-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .page-title {
    font-size: 1.75rem;
  }

  .profile-four-grid {
    grid-template-columns: 1fr;
  }

  .bottom-action-bar {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .bottom-action-buttons {
    flex-direction: column;
    width: 100%;
  }

  .bottom-action-buttons button,
  .back-btn {
    width: 100%;
  }
}
</style>
