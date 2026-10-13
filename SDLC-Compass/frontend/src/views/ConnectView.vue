<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const store = useSessionStore()

// State
const activeTab = ref<'git' | 'zip'>('git')
const gitUrl = ref<string>('https://github.com/sample/atlas-service.git')
const selectedFile = ref<File | null>(null)
const isDragging = ref<boolean>(false)
const validationError = ref<string>('')

// Tab switching
function setTab(tab: 'git' | 'zip') {
  activeTab.value = tab
  validationError.value = ''
}

// File drop handling
function handleDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    const file = e.dataTransfer.files[0]
    if (file.name.endsWith('.zip') || file.type.includes('zip')) {
      selectedFile.value = file
      activeTab.value = 'zip'
      validationError.value = ''
    } else {
      validationError.value = 'Please select a valid ZIP archive (.zip).'
    }
  }
}

function handleFileInput(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    selectedFile.value = file
    validationError.value = ''
  }
}

function triggerFileInput() {
  const fileInput = document.getElementById('zip-file-input') as HTMLInputElement
  fileInput?.click()
}

// Quick sample fill
function fillSampleRepo() {
  activeTab.value = 'git'
  gitUrl.value = 'https://github.com/sample/atlas-service.git'
  validationError.value = ''
}

// Form Submission / Scan Action
async function handleScan() {
  validationError.value = ''

  if (activeTab.value === 'git') {
    const trimmed = gitUrl.value.trim()
    if (!trimmed) {
      validationError.value = 'Please provide a repository Git URL.'
      return
    }
    await store.connectRepository({
      source: 'git',
      gitUrl: trimmed
    })
  } else {
    if (!selectedFile.value) {
      validationError.value = 'Please choose or drop a ZIP archive first.'
      return
    }
    await store.connectRepository({
      source: 'zip',
      file: selectedFile.value
    })
  }

  // Navigate to step 2 on success
  if (store.isConnected && !store.error) {
    router.push('/signals')
  }
}
</script>

<template>
  <div class="connect-view container">
    <!-- Top Step Subtitle Header -->
    <div class="screen-meta">
      <span class="step-badge">TEAM DIAGNOSTIC / STEP 1 OF 5</span>
      <h1 class="page-title">Start with your repository</h1>
      <p class="page-subtitle">
        Connect a codebase to build an evidence-led view of your software delivery lifecycle.
      </p>
    </div>

    <!-- Main 2-Column Content -->
    <div class="connect-grid">
      <!-- Left Column: Source selection, Git input, ZIP dropzone & Privacy notice -->
      <section class="main-card-column">
        <div class="card source-card">
          <div class="card-header">
            <h2 class="card-title">Repository source</h2>
            <p class="card-desc">Use a public Git URL, or upload a ZIP archive.</p>
          </div>

          <!-- Method Tabs -->
          <div class="source-tabs" role="tablist" aria-label="Repository Source Methods">
            <button
              type="button"
              role="tab"
              :aria-selected="activeTab === 'git'"
              class="tab-btn"
              :class="{ 'tab-active': activeTab === 'git' }"
              @click="setTab('git')"
            >
              <svg class="tab-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path
                  fill-rule="evenodd"
                  d="M12.577 4.878a.75.75 0 0 1 .919-.53l2.842.853a.75.75 0 0 1 .505.908l-.853 2.842a.75.75 0 1 1-1.438-.432l.432-1.44-2.877 2.878a4.25 4.25 0 0 0-1.246 3.003v.373a2.25 2.25 0 1 1-1.5 0v-.373c0-1.525.606-2.987 1.684-4.066l2.878-2.877-1.44.432a.75.75 0 0 1-.906-.64Zm-3.452 9.006a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0ZM4.5 6.75a2.25 2.25 0 1 1 3 2.122v2.256a2.25 2.25 0 1 1-1.5 0V8.872A2.25 2.25 0 0 1 4.5 6.75Zm1.5.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 6a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
                  clip-rule="evenodd"
                />
              </svg>
              <span>Git repository</span>
              <span v-if="activeTab === 'git'" class="check-pill" aria-hidden="true">✓</span>
            </button>

            <button
              type="button"
              role="tab"
              :aria-selected="activeTab === 'zip'"
              class="tab-btn"
              :class="{ 'tab-active': activeTab === 'zip' }"
              @click="setTab('zip')"
            >
              <svg class="tab-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path
                  fill-rule="evenodd"
                  d="M4.5 2A1.5 1.5 0 0 0 3 3.5v13A1.5 1.5 0 0 0 4.5 18h11a1.5 1.5 0 0 0 1.5-1.5V7.621a1.5 1.5 0 0 0-.44-1.06l-4.12-4.122A1.5 1.5 0 0 0 11.378 2H4.5Zm4.75 6.75a.75.75 0 0 1 1.5 0v2.546l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 1 1 1.06-1.06l.72.72V8.75Z"
                  clip-rule="evenodd"
                />
              </svg>
              <span>ZIP archive</span>
              <span v-if="activeTab === 'zip'" class="check-pill" aria-hidden="true">✓</span>
            </button>
          </div>

          <!-- Git URL Section -->
          <div v-if="activeTab === 'git'" class="input-panel">
            <div class="field-label-group">
              <label for="git-repo-url" class="field-label">Git URL</label>
              <span class="required-tag">Required</span>
            </div>

            <div class="input-group">
              <input
                id="git-repo-url"
                v-model="gitUrl"
                type="url"
                class="text-input"
                placeholder="https://github.com/organization/project.git"
                aria-describedby="git-help-text"
                @keydown.enter="handleScan"
              />
              <div class="input-icon-adornment" aria-hidden="true">
                <svg viewBox="0 0 16 16" fill="currentColor">
                  <path
                    d="M4.715 6.542 3.343 7.914a3 3 0 1 0 4.243 4.243l1.828-1.829A3 3 0 0 0 8.586 5.5L8 6.086a1 1 0 0 0-.154.199 2 2 0 0 1 .861 3.337L7.335 10.994a1.5 1.5 0 0 1-2.122-2.122l.97-.97A2 2 0 0 1 4.715 6.542Z"
                  />
                  <path
                    d="m11.285 9.458 1.372-1.372a3 3 0 0 0-4.243-4.243L6.586 5.672A3 3 0 0 0 7.414 10.5l.586-.586a1 1 0 0 0 .154-.199 2 2 0 0 1-.861-3.337l1.372-1.372a1.5 1.5 0 1 1 2.122 2.122l-.97.97a2 2 0 0 1 1.472 1.36Z"
                  />
                </svg>
              </div>
            </div>

            <div id="git-help-text" class="input-help-row">
              <span class="help-text">Public GitHub, GitLab, or Bitbucket repository URL.</span>
              <button type="button" class="sample-link-btn" @click="fillSampleRepo">
                Use sample repo (Atlas Service)
              </button>
            </div>
          </div>

          <!-- ZIP Drop Zone Section -->
          <div v-else class="input-panel">
            <div class="field-label-group">
              <label class="field-label">Upload codebase archive</label>
              <span class="required-tag">Required</span>
            </div>

            <div
              class="dropzone-box"
              :class="{ 'dropzone-active': isDragging, 'dropzone-has-file': !!selectedFile }"
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
              @drop="handleDrop"
              @click="triggerFileInput"
              role="button"
              tabindex="0"
              @keydown.enter="triggerFileInput"
            >
              <input
                id="zip-file-input"
                type="file"
                accept=".zip"
                class="sr-only"
                @change="handleFileInput"
              />

              <div class="dropzone-content">
                <div class="upload-icon-circle" aria-hidden="true">
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path
                      d="M9.25 13.25a.75.75 0 0 0 1.5 0V4.636l2.955 3.129a.75.75 0 0 0 1.09-1.03l-4.25-4.5a.75.75 0 0 0-1.09 0l-4.25 4.5a.75.75 0 1 0 1.09 1.03L9.25 4.636v8.614Z"
                    />
                    <path
                      d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z"
                    />
                  </svg>
                </div>

                <div v-if="selectedFile" class="file-chosen-info">
                  <strong class="file-name">{{ selectedFile.name }}</strong>
                  <span class="file-size">({{ (selectedFile.size / 1024).toFixed(1) }} KB)</span>
                  <span class="file-change-hint">Click or drop to replace</span>
                </div>
                <div v-else class="drop-text-group">
                  <span class="drop-primary">Drag & drop a ZIP archive here, or choose file</span>
                  <span class="drop-secondary">Supports .zip archives containing up to ~50 code files</span>
                </div>

                <button type="button" class="btn-secondary drop-action-btn" @click.stop="triggerFileInput">
                  {{ selectedFile ? 'Change archive' : 'Choose ZIP' }}
                </button>
              </div>
            </div>
          </div>

          <!-- Validation Warning -->
          <div v-if="validationError" class="validation-msg" role="alert">
            <svg class="alert-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path
                fill-rule="evenodd"
                d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14Zm.75-10.25a.75.75 0 0 0-1.5 0v4.5a.75.75 0 0 0 1.5 0v-4.5Zm-.75 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
                clip-rule="evenodd"
              />
            </svg>
            <span>{{ validationError }}</span>
          </div>

          <!-- Privacy & Consent Notice (Short privacy sentence per requirements) -->
          <div class="privacy-box">
            <div class="privacy-icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path
                  fill-rule="evenodd"
                  d="M10 1a4.5 4.5 0 0 0-4.5 4.5V9H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-.5V5.5A4.5 4.5 0 0 0 10 1Zm3 8V5.5a3 3 0 1 0-6 0V9h6Z"
                  clip-rule="evenodd"
                />
              </svg>
            </div>
            <p class="privacy-text">
              <strong>Privacy notice:</strong> Code is processed in memory and deleted immediately after scanning.
              Only extracted structural signals are shared with the AI service; full source code is never stored or transmitted.
            </p>
          </div>

          <!-- Bottom Action Row -->
          <div class="card-footer-action">
            <span class="footer-note">Your team stays in control of what is reviewed and shared.</span>
            <button
              type="button"
              class="btn-primary scan-btn"
              :disabled="store.isLoading"
              @click="handleScan"
            >
              <span>Scan repository</span>
              <svg class="btn-arrow" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path
                  fill-rule="evenodd"
                  d="M6.22 3.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06Z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      </section>

      <!-- Right Column: PoC Scope & What Comes Next cards -->
      <aside class="sidebar-column">
        <!-- Supported Scope Card -->
        <div class="card scope-card">
          <div class="scope-tag-row">
            <span class="badge badge-purple">SUPPORTED POC SCOPE</span>
          </div>
          <h2 class="sidebar-card-title">A focused codebase. A clearer starting point.</h2>
          <p class="scope-body">
            Designed for approximately 50 code files in Python, JavaScript, or Java.
          </p>

          <div class="scope-divider"></div>

          <div class="excluded-block">
            <span class="excluded-label">Excluded from analysis</span>
            <p class="excluded-text">
              <code>node_modules</code> · <code>.git</code> · binaries · generated build artifacts
            </p>
          </div>

          <p class="scope-footnote">
            For larger repositories, choose a supported subset. Scope warnings will be surfaced during signal review.
          </p>
        </div>

        <!-- What Comes Next Card -->
        <div class="card next-card">
          <h2 class="sidebar-card-title">What comes next</h2>

          <ul class="steps-preview-list">
            <li class="preview-item">
              <div class="preview-icon-wrap" aria-hidden="true">
                <svg viewBox="0 0 20 20" fill="currentColor">
                  <path
                    d="M10 2a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 10 2ZM10 15a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 10 15ZM10 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"
                  />
                  <path
                    fill-rule="evenodd"
                    d="M3 4.25A2.25 2.25 0 0 1 5.25 2h9.5A2.25 2.25 0 0 1 17 4.25v11.5A2.25 2.25 0 0 1 14.75 18h-9.5A2.25 2.25 0 0 1 3 15.75V4.25Zm2.25-.75a.75.75 0 0 0-.75.75v11.5c0 .414.336.75.75.75h9.5a.75.75 0 0 0 .75-.75V4.25a.75.75 0 0 0-.75-.75h-9.5Z"
                    clip-rule="evenodd"
                  />
                </svg>
              </div>
              <div class="preview-text">
                <strong>Review repository signals</strong>
                <p>Check languages, stack, delivery setup, and estimated quality indicators.</p>
              </div>
            </li>

            <li class="preview-item">
              <div class="preview-icon-wrap" aria-hidden="true">
                <svg viewBox="0 0 20 20" fill="currentColor">
                  <path
                    d="M10 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM6 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM1.49 15.326a.78.78 0 0 1-.358-.442 3 3 0 0 1 4.308-3.516 6.484 6.484 0 0 0-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 0 1-2.07-.655ZM16.44 11.368a3 3 0 0 1 4.309 3.516.78.78 0 0 1-.358.442 4.97 4.97 0 0 1-2.07.655c.039-.212.048-.432.025-.654a6.484 6.484 0 0 0-1.906-3.959ZM18 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM14 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm-4 9a6 6 0 0 0 6-6H4a6 6 0 0 0 6 6Z"
                  />
                </svg>
              </div>
              <div class="preview-text">
                <strong>Add your team perspective</strong>
                <p>Clarify ways of working, friction points, and current AI tools in an interactive chat.</p>
              </div>
            </li>

            <li class="preview-item">
              <div class="preview-icon-wrap" aria-hidden="true">
                <svg viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.857-9.809a.75.75 0 0 0-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 1 0-1.06 1.061l2.5 2.5a.75.75 0 0 0 1.137-.089l4-5.5Z"
                    clip-rule="evenodd"
                  />
                </svg>
              </div>
              <div class="preview-text">
                <strong>Receive phase recommendations</strong>
                <p>Prioritised practices with concrete evidence, expected impact, and adoption effort.</p>
              </div>
            </li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.connect-view {
  padding-top: 2.25rem;
  padding-bottom: 3.5rem;
}

.screen-meta {
  margin-bottom: 2rem;
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
  max-width: 640px;
}

/* 2-Column Layout */
.connect-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 2rem;
  align-items: start;
}

.main-card-column {
  display: flex;
  flex-direction: column;
}

.source-card {
  padding: 2rem;
}

.card-header {
  margin-bottom: 1.5rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.card-desc {
  font-size: 0.9375rem;
  color: var(--color-text-muted);
}

/* Method Tabs */
.source-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.tab-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  min-height: 52px;
}

.tab-btn:hover {
  background-color: var(--color-surface-hover);
  border-color: var(--color-border-strong);
}

.tab-btn.tab-active {
  border-color: var(--color-primary);
  background-color: var(--color-primary-light);
  color: var(--color-primary);
}

.tab-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.check-pill {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background-color: var(--color-primary);
  color: #ffffff;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 0.25rem;
}

/* Input Section */
.input-panel {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  margin-bottom: 1.5rem;
}

.field-label-group {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.field-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.required-tag {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.input-group {
  position: relative;
  display: flex;
  align-items: center;
}

.text-input {
  width: 100%;
  min-height: 50px;
  padding: 0.75rem 2.75rem 0.75rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-family: inherit;
  color: var(--color-text-primary);
  background-color: var(--color-surface);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.text-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.input-icon-adornment {
  position: absolute;
  right: 1rem;
  width: 18px;
  height: 18px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.input-icon-adornment svg {
  width: 100%;
  height: 100%;
}

.input-help-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8125rem;
  gap: 0.5rem;
}

.help-text {
  color: var(--color-text-muted);
}

.sample-link-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  min-height: auto;
  text-decoration: underline;
}

.sample-link-btn:hover {
  color: var(--color-primary-hover);
}

/* Dropzone */
.dropzone-box {
  border: 2px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  background-color: #fafbfd;
  padding: 2.25rem 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropzone-box:hover,
.dropzone-box.dropzone-active {
  border-color: var(--color-primary);
  background-color: var(--color-primary-light);
}

.dropzone-box.dropzone-has-file {
  border-color: var(--color-success-border);
  background-color: var(--color-success-bg);
}

.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.upload-icon-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-icon-circle svg {
  width: 22px;
  height: 22px;
}

.drop-text-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.drop-primary {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.drop-secondary {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.file-chosen-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.file-name {
  font-size: 1rem;
  color: var(--color-text-primary);
}

.file-size {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.file-change-hint {
  font-size: 0.75rem;
  color: var(--color-primary);
  margin-top: 0.25rem;
}

.drop-action-btn {
  margin-top: 0.5rem;
}

/* Validation Message */
.validation-msg {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  color: var(--color-danger-text);
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  margin-bottom: 1.25rem;
}

.alert-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* Privacy Box */
.privacy-box {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
  background-color: #f8fafc;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
  margin-bottom: 1.75rem;
}

.privacy-icon {
  width: 18px;
  height: 18px;
  color: var(--color-text-muted);
  flex-shrink: 0;
  margin-top: 2px;
}

.privacy-icon svg {
  width: 100%;
  height: 100%;
}

.privacy-text {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

/* Footer Action */
.card-footer-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.footer-note {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.scan-btn {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
  font-weight: 600;
  font-size: 0.9375rem;
}

.btn-arrow {
  width: 16px;
  height: 16px;
}

/* Sidebar Cards */
.sidebar-column {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.sidebar-card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.35;
  margin-bottom: 0.75rem;
}

.scope-card {
  padding: 1.75rem;
}

.scope-tag-row {
  margin-bottom: 1rem;
}

.scope-body {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin-bottom: 1.25rem;
}

.scope-divider {
  height: 1px;
  background-color: var(--color-border);
  margin-bottom: 1.25rem;
}

.excluded-block {
  margin-bottom: 1rem;
}

.excluded-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-muted);
  letter-spacing: 0.03em;
  margin-bottom: 0.375rem;
}

.excluded-text {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.excluded-text code {
  font-family: var(--font-family-mono);
  background-color: #f1f5f9;
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
}

.scope-footnote {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  line-height: 1.45;
}

.next-card {
  padding: 1.75rem;
}

.steps-preview-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-top: 1rem;
}

.preview-item {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
}

.preview-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.preview-icon-wrap svg {
  width: 18px;
  height: 18px;
}

.preview-text strong {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 0.25rem;
}

.preview-text p {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

/* Responsive */
@media (max-width: 960px) {
  .connect-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .page-title {
    font-size: 1.75rem;
  }

  .source-card {
    padding: 1.25rem;
  }

  .card-footer-action {
    flex-direction: column;
    align-items: stretch;
  }

  .scan-btn {
    width: 100%;
  }

  .input-help-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
