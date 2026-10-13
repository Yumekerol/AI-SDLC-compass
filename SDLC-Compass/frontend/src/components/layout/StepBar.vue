<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const store = useSessionStore()

interface Step {
  id: number
  title: string
  route: string
}

const steps: Step[] = [
  { id: 1, title: 'Connect repository', route: '/' },
  { id: 2, title: 'Review signals', route: '/signals' },
  { id: 3, title: 'Team context & questions', route: '/questions' },
  { id: 4, title: 'Diagnostic report', route: '/report' },
  { id: 5, title: 'Advisor chat', route: '/advisor' }
]

const currentStepNumber = computed(() => {
  return (route.meta.step as number) || store.currentStep
})

function getStepStatus(stepId: number): 'complete' | 'current' | 'upcoming' {
  if (stepId < currentStepNumber.value) return 'complete'
  if (stepId === currentStepNumber.value) return 'current'
  return 'upcoming'
}

function getStepSubtext(stepId: number): string {
  const status = getStepStatus(stepId)
  if (status === 'complete') return 'Complete'
  if (status === 'current') return 'Current step'
  return 'Up next'
}

function canNavigate(step: Step): boolean {
  // Can always navigate to step 1
  if (step.id === 1) return true
  // Can navigate to step 2 if repo is connected
  if (step.id === 2) return store.isConnected
  // Can navigate to step 3 if signals exist
  if (step.id === 3) return store.isConnected
  // Can navigate to step 4 if diagnostic generated or has answers
  if (step.id === 4) return store.hasDiagnostic || store.isConnected
  // Can navigate to step 5 if advisor is accessible
  if (step.id === 5) return store.hasDiagnostic || store.isConnected
  return false
}

function navigateToStep(step: Step) {
  if (canNavigate(step)) {
    store.setStep(step.id)
    router.push(step.route)
  }
}
</script>

<template>
  <nav class="stepbar-wrapper" aria-label="Diagnostic progress">
    <div class="stepbar-inner container">
      <ol class="step-list">
        <li
          v-for="step in steps"
          :key="step.id"
          class="step-item"
          :class="{
            'step-complete': getStepStatus(step.id) === 'complete',
            'step-current': getStepStatus(step.id) === 'current',
            'step-upcoming': getStepStatus(step.id) === 'upcoming',
            'step-clickable': canNavigate(step)
          }"
          @click="navigateToStep(step)"
          :aria-current="getStepStatus(step.id) === 'current' ? 'step' : undefined"
          role="button"
          :tabindex="canNavigate(step) ? 0 : -1"
          @keydown.enter="navigateToStep(step)"
        >
          <!-- Indicator circle / icon -->
          <div class="step-indicator">
            <template v-if="getStepStatus(step.id) === 'complete'">
              <svg class="check-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path
                  fill-rule="evenodd"
                  d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
                  clip-rule="evenodd"
                />
              </svg>
            </template>
            <template v-else>
              <span>{{ step.id }}</span>
            </template>
          </div>

          <!-- Step label & status description -->
          <div class="step-details">
            <span class="step-title">{{ step.title }}</span>
            <span class="step-subtext">{{ getStepSubtext(step.id) }}</span>
          </div>
        </li>
      </ol>
    </div>
  </nav>
</template>

<style scoped>
.stepbar-wrapper {
  background-color: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 0.875rem 0;
}

.step-list {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  list-style: none;
  overflow-x: auto;
  scrollbar-width: none;
}

.step-list::-webkit-scrollbar {
  display: none;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 170px;
  padding: 0.5rem 0.625rem;
  border-radius: var(--radius-md);
  transition: background-color 0.15s ease;
}

.step-clickable {
  cursor: pointer;
}

.step-clickable:hover {
  background-color: var(--color-surface-hover);
}

.step-indicator {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8125rem;
  font-weight: 600;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

/* Status variants */
.step-upcoming .step-indicator {
  background-color: #f1f5f9;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}

.step-current .step-indicator {
  background-color: var(--color-primary);
  color: var(--color-text-inverted);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.step-complete .step-indicator {
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  border: 1px solid var(--color-primary-border);
}

.check-icon {
  width: 16px;
  height: 16px;
}

.step-details {
  display: flex;
  flex-direction: column;
}

.step-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.25;
  white-space: nowrap;
}

.step-upcoming .step-title {
  color: var(--color-text-muted);
}

.step-subtext {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.2;
}

.step-current .step-subtext {
  color: var(--color-primary);
  font-weight: 500;
}

@media (max-width: 900px) {
  .step-details {
    display: none;
  }
  .step-item {
    min-width: auto;
    flex: initial;
    padding: 0.25rem;
  }
}
</style>
