<script setup lang="ts">
defineProps<{
  scopeItems: string[]
  roadmapItems: string[]
}>()
</script>

<template>
  <div class="scope-limitations-section">
    <!-- Left Card: Current PoC Scope & Enterprise Roadmap -->
    <div class="card scope-box">
      <div class="scope-inner-group">
        <h3 class="section-heading">Scope, limitations & next horizon</h3>

        <div class="scope-block">
          <span class="block-badge badge badge-poc">CURRENT POC SCOPE</span>
          <ul class="scope-bullet-list">
            <li v-for="(item, idx) in scopeItems" :key="idx" class="bullet-item">
              <span class="bullet-dot" aria-hidden="true">•</span>
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>

        <div class="roadmap-block">
          <span class="roadmap-heading">Enterprise roadmap · Future scope, not available today</span>
          <ul class="scope-bullet-list">
            <li v-for="(item, idx) in roadmapItems" :key="idx" class="bullet-item">
              <span class="bullet-dot" aria-hidden="true">•</span>
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Right Card: Review-Ready PDF Structure Preview -->
    <div class="card pdf-structure-box">
      <h3 class="section-heading">A review-ready PDF structure</h3>
      <p class="pdf-desc">
        Designed output for stakeholder review, carrying sample data and report version.
      </p>

      <ul class="pdf-checklist">
        <li class="check-item">
          <span class="check-icon-pill" aria-hidden="true">✓</span>
          <span>Cover & report metadata</span>
        </li>
        <li class="check-item">
          <span class="check-icon-pill" aria-hidden="true">✓</span>
          <span>Executive summary</span>
        </li>
        <li class="check-item">
          <span class="check-icon-pill" aria-hidden="true">✓</span>
          <span>Repository & team context profile</span>
        </li>
        <li class="check-item">
          <span class="check-icon-pill" aria-hidden="true">✓</span>
          <span>All six phase recommendations</span>
        </li>
        <li class="check-item">
          <span class="check-icon-pill" aria-hidden="true">✓</span>
          <span>Evidence, scope & limitations</span>
        </li>
      </ul>

      <p class="pdf-footnote">
        Export PDF is a static snapshot of the selected version.
      </p>
    </div>
  </div>
</template>

<style scoped>
.scope-limitations-section {
  display: grid;
  grid-template-columns: 1.8fr 1.2fr;
  gap: 2rem;
  align-items: start;
  margin-top: 1.5rem;
  margin-bottom: 2.5rem;
}

.scope-box,
.pdf-structure-box {
  padding: 1.75rem 2rem;
  height: 100%;
}

.section-heading {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 1rem;
}

.scope-inner-group {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.scope-block {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.block-badge {
  align-self: flex-start;
}

.scope-bullet-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.bullet-item {
  display: flex;
  align-items: flex-start;
  gap: 0.625rem;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.bullet-dot {
  color: var(--color-primary);
  font-size: 1.125rem;
  line-height: 1;
}

.roadmap-block {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border-subtle);
}

.roadmap-heading {
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

/* Right Column PDF Preview */
.pdf-desc {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.45;
  margin-bottom: 1.25rem;
}

.pdf-checklist {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: var(--color-text-primary);
  font-weight: 500;
}

.check-icon-pill {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
}

.pdf-footnote {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.4;
  border-top: 1px solid var(--color-border-subtle);
  padding-top: 0.75rem;
}

@media (max-width: 960px) {
  .scope-limitations-section {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
}
</style>
