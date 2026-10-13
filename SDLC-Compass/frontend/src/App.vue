<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
import StepBar from '@/components/layout/StepBar.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { useSessionStore } from '@/stores/session'

const store = useSessionStore()
</script>

<template>
  <div class="app-layout">
    <!-- Top Bar -->
    <AppHeader />

    <!-- Persistent Diagnostic Stepper -->
    <StepBar />

    <!-- Global Error Display (preserves user state with safe retry) -->
    <div v-if="store.error" class="container">
      <ErrorState
        :error="store.error"
        @retry="store.retryLastAction()"
        @dismiss="store.clearError()"
      />
    </div>

    <!-- Active Step Content -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- Global Async Loading Overlay -->
    <LoadingOverlay
      v-if="store.isLoading"
      :message="store.loadingMessage"
    />

    <!-- Global Subdued Footer -->
    <footer class="app-footer">
      <div class="footer-inner container">
        <span>Independent concept · Not affiliated with or endorsed by Accenture</span>
        <span>Static controls · Human review required</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.app-footer {
  border-top: 1px solid var(--color-border);
  background-color: var(--color-surface);
  padding: 1.25rem 0;
  margin-top: auto;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.footer-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

@media (max-width: 640px) {
  .footer-inner {
    flex-direction: column;
    text-align: center;
    gap: 0.5rem;
  }
}
</style>
