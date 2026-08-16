<script setup>
import { formatEta, formatSecPerItem, formatThroughput, formatCount } from '../format.js'

defineProps({
  throughputPerHour: { type: Number, default: null },
  secPerItem: { type: Number, default: null },
  etaSeconds: { type: Number, default: null },
  errors: { type: Number, default: 0 },
})
</script>

<template>
  <section class="panel stat-grid">
    <div class="stat">
      <div class="stat-value">{{ formatThroughput(throughputPerHour) }}</div>
      <div class="stat-label">throughput</div>
    </div>
    <div class="stat">
      <div class="stat-value">{{ formatSecPerItem(secPerItem) }}</div>
      <div class="stat-label">pace</div>
    </div>
    <div class="stat">
      <div class="stat-value">ETA {{ formatEta(etaSeconds) }}</div>
      <div class="stat-label">time remaining</div>
    </div>
    <div class="stat" :class="{ 'stat--danger': errors > 0 }">
      <div class="stat-value">Errors {{ formatCount(errors) }}</div>
      <div class="stat-label">llm errors</div>
    </div>
  </section>
</template>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 24px;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
}

.stat-label {
  font-size: 11px;
  color: var(--text-dim);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-top: 2px;
}

.stat--danger .stat-value {
  color: var(--red);
}
</style>
