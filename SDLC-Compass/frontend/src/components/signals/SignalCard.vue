<script setup lang="ts">
defineProps<{
  title: string
  badgeText?: string
  badgeClass?: string
  sampleEvidence?: string
}>()

const emit = defineEmits<{
  (e: 'edit'): void
}>()
</script>

<template>
  <div class="card signal-card">
    <!-- Header: Icon, Title & Edit Button -->
    <div class="card-top-row">
      <div class="title-with-icon">
        <div class="card-icon" aria-hidden="true">
          <slot name="icon"></slot>
        </div>
        <h3 class="card-heading">{{ title }}</h3>
      </div>

      <button
        type="button"
        class="edit-action-btn"
        :aria-label="`Edit ${title} signals`"
        @click="emit('edit')"
      >
        <svg class="edit-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path
            d="m13.488 2.513-.997-.997a2.035 2.035 0 0 0-2.879 0L2.73 8.397a1 1 0 0 0-.265.495l-.462 2.775a.5.5 0 0 0 .573.573l2.775-.462a1 1 0 0 0 .495-.265l6.88-6.88a2.036 2.036 0 0 0 .762-2.12Zm-1.88.882.997.997-6.26 6.26-.997-.997 6.26-6.26Z"
          />
        </svg>
        <span>Edit</span>
      </button>
    </div>

    <!-- Confidence Badge -->
    <div v-if="badgeText" class="badge-row">
      <span class="badge" :class="badgeClass || 'badge-purple'">{{ badgeText }}</span>
    </div>

    <!-- Main Signal Content -->
    <div class="card-content">
      <slot></slot>
    </div>

    <!-- Descriptive Footnote -->
    <div v-if="$slots.footnote" class="card-footnote">
      <slot name="footnote"></slot>
    </div>

    <!-- Sample Evidence Footer -->
    <div v-if="sampleEvidence" class="sample-evidence-row">
      <span class="evidence-label">SAMPLE EVIDENCE</span>
      <span class="evidence-value">{{ sampleEvidence }}</span>
    </div>
  </div>
</template>

<style scoped>
.signal-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  height: 100%;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.signal-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
}

.card-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.875rem;
}

.title-with-icon {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.card-icon {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.card-heading {
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.edit-action-btn {
  min-height: 36px;
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-primary);
  background-color: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.edit-action-btn:hover {
  background-color: var(--color-primary-light);
  border-color: var(--color-primary-border);
}

.edit-icon {
  width: 13px;
  height: 13px;
}

.badge-row {
  margin-bottom: 1.25rem;
}

.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.card-footnote {
  margin-top: 1rem;
  padding-top: 0.875rem;
  border-top: 1px solid var(--color-border-subtle);
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  line-height: 1.45;
}

.sample-evidence-row {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border-subtle);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.evidence-label {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.evidence-value {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  font-family: var(--font-family-mono);
  word-break: break-all;
}
</style>
