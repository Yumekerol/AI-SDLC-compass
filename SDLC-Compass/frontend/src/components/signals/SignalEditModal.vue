<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import type { RepoSignals } from '@/types/signals'

export type EditableSignalCategory =
  | 'languages'
  | 'size'
  | 'stack'
  | 'cicd'
  | 'quality'
  | 'warnings'

const props = defineProps<{
  category: EditableSignalCategory
  signals: RepoSignals
}>()

const emit = defineEmits<{
  (e: 'save', updated: RepoSignals): void
  (e: 'close'): void
}>()

// Deep clone for local editing
const localSignals = ref<RepoSignals>(JSON.parse(JSON.stringify(props.signals)))

// Temporary string representations for comma-separated inputs
const stackFrameworks = ref(localSignals.value.stack.frameworks.join(', '))
const stackTesting = ref(localSignals.value.stack.testingLibraries.join(', '))
const stackBuild = ref(localSignals.value.stack.buildTools.join(', '))

// Watch for prop updates
watch(
  () => props.signals,
  (newVal) => {
    localSignals.value = JSON.parse(JSON.stringify(newVal))
    stackFrameworks.value = localSignals.value.stack.frameworks.join(', ')
    stackTesting.value = localSignals.value.stack.testingLibraries.join(', ')
    stackBuild.value = localSignals.value.stack.buildTools.join(', ')
  },
  { deep: true }
)

// Keyboard escape listener
function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

function getCategoryTitle(cat: EditableSignalCategory): string {
  switch (cat) {
    case 'languages':
      return 'Edit Language Breakdown'
    case 'size':
      return 'Edit Size & Structure Estimates'
    case 'stack':
      return 'Edit Stack & Tooling'
    case 'cicd':
      return 'Edit CI/CD & Operations'
    case 'quality':
      return 'Edit Quality & Coverage Indicators'
    case 'warnings':
      return 'Edit Warnings & Missing Signals'
  }
}

function handleSave() {
  // Sync comma-separated inputs if editing stack
  if (props.category === 'stack') {
    localSignals.value.stack.frameworks = stackFrameworks.value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    localSignals.value.stack.testingLibraries = stackTesting.value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    localSignals.value.stack.buildTools = stackBuild.value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  }

  // Recalculate test-to-code ratio if quality counts changed
  if (props.category === 'quality') {
    const total = localSignals.value.quality.sourceFilesCount
    const tests = localSignals.value.quality.testFilesCount
    if (total > 0) {
      localSignals.value.quality.testToCodeRatio = parseFloat(((tests / total) * 100).toFixed(1))
    }
  }

  emit('save', localSignals.value)
}

function removeLanguage(index: number) {
  localSignals.value.languages.splice(index, 1)
}

function addLanguage() {
  localSignals.value.languages.push({
    name: 'New Language',
    files: 5,
    percentage: 10
  })
}

function removeWarning(index: number) {
  localSignals.value.warnings.splice(index, 1)
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')" role="presentation">
    <div
      class="modal-window card"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <!-- Modal Header -->
      <div class="modal-header">
        <h2 id="modal-title" class="modal-title">{{ getCategoryTitle(category) }}</h2>
        <button
          type="button"
          class="close-btn"
          aria-label="Close dialog"
          @click="emit('close')"
        >
          &times;
        </button>
      </div>

      <!-- Modal Body (Conditional per category) -->
      <div class="modal-body">
        <!-- 1. Languages Form -->
        <div v-if="category === 'languages'" class="form-section">
          <p class="section-hint">
            Adjust the detected languages, file counts, and estimated codebase proportions.
          </p>

          <div
            v-for="(lang, idx) in localSignals.languages"
            :key="idx"
            class="lang-edit-row"
          >
            <div class="form-field flex-2">
              <label :for="`lang-name-${idx}`">Language</label>
              <input
                :id="`lang-name-${idx}`"
                v-model="lang.name"
                type="text"
                class="form-input"
              />
            </div>
            <div class="form-field flex-1">
              <label :for="`lang-files-${idx}`">Files</label>
              <input
                :id="`lang-files-${idx}`"
                v-model.number="lang.files"
                type="number"
                min="0"
                class="form-input"
              />
            </div>
            <div class="form-field flex-1">
              <label :for="`lang-pct-${idx}`">Percentage (%)</label>
              <input
                :id="`lang-pct-${idx}`"
                v-model.number="lang.percentage"
                type="number"
                min="0"
                max="100"
                class="form-input"
              />
            </div>
            <button
              type="button"
              class="btn-ghost icon-only-btn"
              title="Remove language"
              aria-label="Remove language"
              @click="removeLanguage(idx)"
            >
              🗑️
            </button>
          </div>

          <button type="button" class="btn-secondary add-btn" @click="addLanguage">
            + Add Language
          </button>
        </div>

        <!-- 2. Size & Structure Form -->
        <div v-else-if="category === 'size'" class="form-section">
          <div class="form-grid">
            <div class="form-field">
              <label for="size-code-files">Total Code Files</label>
              <input
                id="size-code-files"
                v-model.number="localSignals.size.codeFiles"
                type="number"
                min="1"
                class="form-input"
              />
            </div>

            <div class="form-field">
              <label for="size-loc">LOC Estimate (Lines of Code)</label>
              <input
                id="size-loc"
                v-model.number="localSignals.size.locEstimate"
                type="number"
                min="100"
                class="form-input"
              />
            </div>

            <div class="form-field">
              <label for="size-modules">Module Estimate</label>
              <input
                id="size-modules"
                v-model.number="localSignals.size.moduleEstimate"
                type="number"
                min="1"
                class="form-input"
              />
            </div>

            <div class="form-field">
              <label for="size-complexity">Approximate Complexity</label>
              <select
                id="size-complexity"
                v-model="localSignals.size.approxComplexity"
                class="form-select"
              >
                <option value="Low">Low</option>
                <option value="Moderate">Moderate</option>
                <option value="High">High</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 3. Stack & Tooling Form -->
        <div v-else-if="category === 'stack'" class="form-section">
          <div class="form-field">
            <label for="stack-frameworks">Frameworks (comma separated)</label>
            <input
              id="stack-frameworks"
              v-model="stackFrameworks"
              type="text"
              class="form-input"
              placeholder="e.g. FastAPI, React"
            />
          </div>

          <div class="form-field">
            <label for="stack-testing">Testing Libraries (comma separated)</label>
            <input
              id="stack-testing"
              v-model="stackTesting"
              type="text"
              class="form-input"
              placeholder="e.g. pytest, Vitest, Jest"
            />
          </div>

          <div class="form-field">
            <label for="stack-build">Build Tools (comma separated)</label>
            <input
              id="stack-build"
              v-model="stackBuild"
              type="text"
              class="form-input"
              placeholder="e.g. Vite, pip, npm"
            />
          </div>
        </div>

        <!-- 4. CI/CD & Operations Form -->
        <div v-else-if="category === 'cicd'" class="form-section">
          <div class="form-field">
            <label for="cicd-provider">CI/CD Provider</label>
            <input
              id="cicd-provider"
              v-model="localSignals.cicd.ciProvider"
              type="text"
              class="form-input"
            />
          </div>

          <div class="checkbox-group">
            <label class="custom-checkbox">
              <input v-model="localSignals.cicd.hasBuildJob" type="checkbox" />
              <span>Build Job Detected in CI</span>
            </label>
            <label class="custom-checkbox">
              <input v-model="localSignals.cicd.hasTestJob" type="checkbox" />
              <span>Automated Test Job Detected in CI</span>
            </label>
            <label class="custom-checkbox">
              <input v-model="localSignals.cicd.hasDeployJob" type="checkbox" />
              <span>Deployment Job Detected in CI</span>
            </label>
          </div>

          <div class="form-field">
            <label for="cicd-containers">Containerisation Status</label>
            <input
              id="cicd-containers"
              v-model="localSignals.cicd.containerization"
              type="text"
              class="form-input"
            />
          </div>

          <div class="form-field">
            <label for="cicd-docs">Documentation Found</label>
            <input
              id="cicd-docs"
              v-model="localSignals.cicd.documentation"
              type="text"
              class="form-input"
            />
          </div>
        </div>

        <!-- 5. Quality Indicators Form -->
        <div v-else-if="category === 'quality'" class="form-section">
          <div class="form-grid">
            <div class="form-field">
              <label for="qual-test-files">Test Files Count</label>
              <input
                id="qual-test-files"
                v-model.number="localSignals.quality.testFilesCount"
                type="number"
                min="0"
                class="form-input"
              />
            </div>

            <div class="form-field">
              <label for="qual-src-files">Source Files Count</label>
              <input
                id="qual-src-files"
                v-model.number="localSignals.quality.sourceFilesCount"
                type="number"
                min="1"
                class="form-input"
              />
            </div>
          </div>

          <div class="form-field">
            <label for="qual-coverage">Executed Coverage Status</label>
            <input
              id="qual-coverage"
              v-model="localSignals.quality.executedCoverage"
              type="text"
              class="form-input"
            />
          </div>

          <div class="form-field">
            <label for="qual-gate">Quality Gate in CI</label>
            <input
              id="qual-gate"
              v-model="localSignals.quality.qualityGateStatus"
              type="text"
              class="form-input"
            />
          </div>
        </div>

        <!-- 6. Warnings Form -->
        <div v-else-if="category === 'warnings'" class="form-section">
          <div
            v-for="(w, idx) in localSignals.warnings"
            :key="w.id"
            class="warning-edit-card card"
          >
            <div class="form-field">
              <label :for="`w-title-${idx}`">Warning Title</label>
              <input
                :id="`w-title-${idx}`"
                v-model="w.title"
                type="text"
                class="form-input"
              />
            </div>
            <div class="form-field">
              <label :for="`w-desc-${idx}`">Description</label>
              <textarea
                :id="`w-desc-${idx}`"
                v-model="w.description"
                rows="2"
                class="form-textarea"
              ></textarea>
            </div>
            <button
              type="button"
              class="btn-ghost remove-warning-btn"
              @click="removeWarning(idx)"
            >
              Remove Warning
            </button>
          </div>

          <p v-if="localSignals.warnings.length === 0" class="muted-note">
            No active warnings.
          </p>
        </div>
      </div>

      <!-- Modal Footer Actions -->
      <div class="modal-footer">
        <button type="button" class="btn-secondary" @click="emit('close')">
          Cancel
        </button>
        <button type="button" class="btn-primary" @click="handleSave">
          Apply Changes
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 1rem;
}

.modal-window {
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background-color: var(--color-surface);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: modalScale 0.2s ease-out;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.close-btn {
  width: var(--min-touch-target);
  height: var(--min-touch-target);
  padding: 0;
  background: transparent;
  border: none;
  font-size: 1.5rem;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: var(--color-text-primary);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-hint {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-field label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.form-input,
.form-select,
.form-textarea {
  font-family: inherit;
  font-size: 0.875rem;
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  background-color: var(--color-surface);
  min-height: 44px;
}

.form-textarea {
  min-height: 70px;
  resize: vertical;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.lang-edit-row {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border-subtle);
}

.flex-2 {
  flex: 2;
}

.flex-1 {
  flex: 1;
}

.icon-only-btn {
  min-height: 44px;
  min-width: 44px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-btn {
  align-self: flex-start;
  margin-top: 0.5rem;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.5rem 0;
}

.custom-checkbox {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-size: 0.875rem;
  cursor: pointer;
  min-height: 36px;
}

.custom-checkbox input[type='checkbox'] {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
}

.warning-edit-card {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background-color: #fafbfc;
}

.remove-warning-btn {
  align-self: flex-end;
  font-size: 0.8125rem;
  color: var(--color-danger-text);
  min-height: 36px;
}

.muted-note {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  font-style: italic;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--color-border);
}

@keyframes modalScale {
  from {
    transform: scale(0.96);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .lang-edit-row {
    flex-direction: column;
    align-items: stretch;
  }

  .icon-only-btn {
    align-self: flex-end;
  }
}
</style>
