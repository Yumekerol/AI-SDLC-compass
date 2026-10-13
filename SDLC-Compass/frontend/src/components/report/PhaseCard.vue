<script setup lang="ts">
import type { Recommendation, SdlcPhase } from '@/types/diagnostic'

defineProps<{
  phase: SdlcPhase | string
  phaseTitle: string
  recommendation: Recommendation
}>()

function getPriorityBadgeClass(priority: string): string {
  switch (priority.toLowerCase()) {
    case 'high':
      return 'badge-purple'
    case 'medium':
      return 'badge-info'
    case 'low':
      return 'badge-poc'
    default:
      return 'badge-poc'
  }
}
</script>

<template>
  <div class="card phase-card" :id="`phase-${phase}`">
    <!-- Left Column: Phase identity, Recommendation & Practice -->
    <div class="phase-left-col">
      <!-- Phase Tag & Badges -->
      <div class="phase-identity-row">
        <div class="phase-tag">
          <div class="phase-icon" aria-hidden="true">
            <!-- Requirements & Design Icon -->
            <svg v-if="phase === 'requirements' || phase === 'requirements_design'" viewBox="0 0 20 20" fill="currentColor">
              <path
                d="M3 4a2 2 0 0 0-2 2v1.161l8.441 4.221a1.25 1.25 0 0 0 1.118 0L19 7.162V6a2 2 0 0 0-2-2H3Z"
              />
              <path
                d="m19 8.839-7.77 3.885a2.75 2.75 0 0 1-2.46 0L1 8.839V14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.839Z"
              />
            </svg>
            <!-- Design Icon -->
            <svg v-else-if="phase === 'design'" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M4.25 2A2.25 2.25 0 0 0 2 4.25v11.5A2.25 2.25 0 0 0 4.25 18h11.5A2.25 2.25 0 0 0 18 15.75V4.25A2.25 2.25 0 0 0 15.75 2H4.25Zm0 1.5h11.5c.414 0 .75.336.75.75v1.25H3.5V4.25c0-.414.336-.75.75-.75Zm12.25 3.5H3.5v8.5c0 .414.336.75.75.75h11.5a.75.75 0 0 0 .75-.75V7Z"
                clip-rule="evenodd"
              />
            </svg>
            <!-- Development Icon -->
            <svg v-else-if="phase === 'development' || phase === 'code_refactoring'" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M6.28 5.22a.75.75 0 0 1 0 1.06L2.56 10l3.72 3.72a.75.75 0 0 1-1.06 1.06L.97 10.53a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Zm7.44 0a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L17.44 10l-3.72-3.72a.75.75 0 0 1 0-1.06ZM11.377 2.011a.75.75 0 0 1 .612.867l-2.5 14.5a.75.75 0 0 1-1.478-.256l2.5-14.5a.75.75 0 0 1 .866-.611Z"
                clip-rule="evenodd"
              />
            </svg>
            <!-- Testing Icon -->
            <svg v-else-if="phase === 'testing' || phase === 'qa_testing'" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M9 3.5a1.5 1.5 0 0 1 1.5-1.5h1A1.5 1.5 0 0 1 13 3.5v.75A6.5 6.5 0 0 1 17.5 10v4.75a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 14.75V10A6.5 6.5 0 0 1 9 4.25V3.5ZM10.5 5a5 5 0 0 0-4.5 5v4.75c0 .414.336.75.75.75h8.5a.75.75 0 0 0 .75-.75V10a5 5 0 0 0-4.5-5h-1Z"
                clip-rule="evenodd"
              />
            </svg>
            <!-- Deployment & Monitoring Icon -->
            <svg v-else viewBox="0 0 20 20" fill="currentColor">
              <path
                d="M10 2a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 10 2ZM10 15a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 10 15ZM10 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"
              />
            </svg>
          </div>
          <span class="phase-name">{{ phaseTitle }}</span>
        </div>

        <div class="phase-badges">
          <span v-if="recommendation.quickWin" class="badge badge-success">Quick win</span>
          <span class="badge" :class="getPriorityBadgeClass(recommendation.priority)">
            {{ recommendation.priority }} priority
          </span>
        </div>
      </div>

      <!-- Recommendation Title -->
      <h3 class="recommendation-title">{{ recommendation.title }}</h3>

      <!-- Practice Description / Snippet -->
      <p class="recommendation-narrative">
        {{ recommendation.justification }}
      </p>

      <div class="example-practice-box">
        <span class="practice-label">EXAMPLE PRACTICE:</span>
        <span class="practice-text">{{ recommendation.examplePractice }}</span>
      </div>

      <!-- Impact & Effort Row -->
      <div class="metrics-row">
        <div class="metric-item">
          <span class="metric-key">EXPECTED IMPACT</span>
          <span class="metric-val">{{ recommendation.expectedImpact }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-key">ADOPTION EFFORT</span>
          <span class="metric-val">{{ recommendation.effort }}</span>
        </div>
      </div>
    </div>

    <!-- Right Column: Why this recommendation (Justification Block) -->
    <div class="phase-right-col">
      <div class="justification-card">
        <span class="justification-header">WHY THIS RECOMMENDATION</span>
        <p class="justification-main">{{ recommendation.justification }}</p>
        <p class="justification-sub">
          Recommendations are cross-referenced with your declared team pain points and repository evidence boundaries.
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.phase-card {
  padding: 1.75rem 2rem;
  display: grid;
  grid-template-columns: 1.8fr 1.2fr;
  gap: 2rem;
  align-items: start;
  margin-bottom: 1.5rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.phase-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
}

.phase-left-col {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.phase-identity-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}

.phase-tag {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.phase-icon {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.phase-icon svg {
  width: 100%;
  height: 100%;
}

.phase-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.phase-badges {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.recommendation-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.3;
}

.recommendation-narrative {
  font-size: 0.9375rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.example-practice-box {
  background-color: #fafbfc;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  font-size: 0.8125rem;
  line-height: 1.45;
}

.practice-label {
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
  margin-right: 0.375rem;
}

.practice-text {
  color: var(--color-text-primary);
}

.metrics-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 0.5rem;
  padding-top: 0.875rem;
  border-top: 1px solid var(--color-border-subtle);
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metric-key {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.metric-val {
  font-size: 0.8125rem;
  color: var(--color-text-primary);
  font-weight: 500;
  line-height: 1.4;
}

/* Right Column: Justification Box */
.phase-right-col {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.justification-card {
  background-color: #fafbfd;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  height: 100%;
}

.justification-header {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-primary);
}

.justification-main {
  font-size: 0.875rem;
  color: var(--color-text-primary);
  line-height: 1.5;
  font-weight: 500;
}

.justification-sub {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.45;
  margin-top: auto;
}

@media (max-width: 960px) {
  .phase-card {
    grid-template-columns: 1fr;
    gap: 1.5rem;
    padding: 1.5rem;
  }

  .metrics-row {
    grid-template-columns: 1fr;
  }
}
</style>
