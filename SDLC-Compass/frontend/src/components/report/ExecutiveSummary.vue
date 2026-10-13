<script setup lang="ts">
defineProps<{
  headline: string
  summary: string
  highPriorityCount: number
  quickWinsCount: number
  phasesCoveredCount: number
  isMock?: boolean
}>()
</script>

<template>
  <div class="executive-banner-card">
    <div class="executive-content-left">
      <div class="banner-tag-row">
        <span class="banner-tag">EXECUTIVE SUMMARY<template v-if="isMock"> / SAMPLE DATA</template></span>
      </div>
      <h2 class="executive-headline">{{ headline }}</h2>
      <p class="executive-narrative">{{ summary }}</p>
    </div>

    <div class="executive-stats-right">
      <span class="stats-header-title">RECOMMENDED STARTING POINT</span>
      <div class="stat-pill-group">
        <div class="stat-pill-row">
          <span class="stat-digit">{{ highPriorityCount }}</span>
          <span class="stat-desc">High-priority phases</span>
        </div>
        <div class="stat-pill-row">
          <span class="stat-digit highlight-green">{{ quickWinsCount }}</span>
          <span class="stat-desc">Quick wins to pilot</span>
        </div>
        <div class="stat-pill-row">
          <span class="stat-digit">{{ phasesCoveredCount }}</span>
          <span class="stat-desc">SDLC phases covered</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.executive-banner-card {
  background-color: var(--color-dark-card);
  color: #ffffff;
  border-radius: var(--radius-lg);
  padding: 2.25rem 2.5rem;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 2.5rem;
  align-items: center;
  box-shadow: var(--shadow-lg);
  margin-bottom: 2rem;
  border: 1px solid var(--color-dark-border);
}

.executive-content-left {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.banner-tag-row {
  display: flex;
  align-items: center;
}

.banner-tag {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #a5b4fc;
}

.executive-headline {
  font-size: 1.75rem;
  font-weight: 800;
  line-height: 1.25;
  color: #ffffff;
  letter-spacing: -0.02em;
}

.executive-narrative {
  font-size: 0.9375rem;
  line-height: 1.6;
  color: #cbd5e1;
}

.executive-stats-right {
  background-color: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stats-header-title {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #94a3b8;
  text-transform: uppercase;
}

.stat-pill-group {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.stat-pill-row {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.stat-digit {
  font-size: 1.875rem;
  font-weight: 800;
  line-height: 1;
  color: #ffffff;
  min-width: 24px;
}

.stat-digit.highlight-green {
  color: #4ade80;
}

.stat-desc {
  font-size: 0.8125rem;
  color: #cbd5e1;
  font-weight: 500;
}

@media (max-width: 900px) {
  .executive-banner-card {
    grid-template-columns: 1fr;
    padding: 1.5rem;
    gap: 1.5rem;
  }
}
</style>
