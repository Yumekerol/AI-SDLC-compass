<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner container">
      <!-- Left: Logo & Proof of Concept tag -->
      <div class="brand-group" @click="goHome" role="button" tabindex="0" @keydown.enter="goHome">
        <div class="logo-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="24" height="24" rx="6" fill="#6D3CC8" />
            <circle cx="12" cy="12" r="7" stroke="#FFFFFF" stroke-width="2" />
            <polygon points="12,7 14.5,12 12,11" fill="#FFFFFF" />
            <polygon points="12,17 9.5,12 12,13" fill="#A5B4FC" />
          </svg>
        </div>
        <div class="brand-text">
          <span class="app-title">AI-SDLC Compass</span>
          <span class="badge badge-poc">PROOF OF CONCEPT</span>
        </div>
      </div>

      <!-- Right: Delivery workspace & Team profile avatar -->
      <div class="workspace-profile">
        <span class="workspace-label">Delivery workspace</span>
        <div class="user-pill" title="Current session user">
          <div class="avatar-circle">TL</div>
          <span class="user-name">Team representative</span>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: var(--header-height);
  background-color: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 40;
}

.header-inner {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  user-select: none;
}

.logo-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.brand-text {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.app-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.workspace-profile {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.workspace-label {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.avatar-circle {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

@media (max-width: 640px) {
  .workspace-label {
    display: none;
  }
  .user-name {
    display: none;
  }
}
</style>
