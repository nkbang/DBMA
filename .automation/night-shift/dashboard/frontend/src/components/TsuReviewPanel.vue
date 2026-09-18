<script setup>
import { computed } from 'vue'

const props = defineProps({
  review: { type: Object, default: null },
})

const sourceLabels = {
  Dagg_Church_Order: 'Dagg, Church Order',
  Hiscox_Standard_Manual: 'Hiscox, Standard Manual',
  Fuller_Complete_Works_Vol08: 'Fuller Works Vol.08',
}

function label(identifier) {
  return sourceLabels[identifier] || identifier
}

const pct = computed(() => {
  if (!props.review || !props.review.total) return 0
  return Math.round((props.review.verified / props.review.total) * 1000) / 10
})
</script>

<template>
  <section class="panel tsu-review-panel" v-if="review">
    <div class="panel-head">
      <h3 class="panel-title">TSU Human Review</h3>
      <span class="badge" :class="review.complete ? 'badge--complete' : 'badge--running'">
        {{ review.complete ? 'COMPLETE' : 'IN PROGRESS' }}
      </span>
    </div>

    <div class="totals-row">
      <div class="totals-bar">
        <div class="totals-bar-fill" :style="{ width: pct + '%' }"></div>
      </div>
      <div class="totals-text">
        verified {{ review.verified.toLocaleString() }} · rejected {{ review.rejected.toLocaleString() }}
        · pending {{ review.generated.toLocaleString() }} / {{ review.total.toLocaleString() }} ({{ pct }}%)
      </div>
    </div>

    <div class="legend-row">
      <span class="legend-item"><span class="stat stat--verified">●</span> verified</span>
      <span class="legend-item"><span class="stat stat--rejected">●</span> rejected</span>
      <span class="legend-item"><span class="stat stat--pending">●</span> pending</span>
    </div>

    <div class="source-row" v-for="s in review.sources" :key="s.identifier">
      <span class="source-label">{{ label(s.identifier) }}</span>
      <span class="source-stats">
        <span class="stat stat--verified" title="verified">{{ s.verified.toLocaleString() }}</span>
        <span class="stat stat--rejected" title="rejected">{{ s.rejected.toLocaleString() }}</span>
        <span class="stat stat--pending" :class="{ 'stat--pending-active': s.generated }" title="pending">{{ s.generated.toLocaleString() }}</span>
        <span class="stat-total">of {{ s.total.toLocaleString() }}</span>
      </span>
    </div>
  </section>
</template>

<style scoped>
.tsu-review-panel {
  padding-bottom: 24px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.badge {
  font-size: 10px;
  letter-spacing: 0.06em;
}

.badge--complete {
  color: #4fa8ff;
}

.badge--running {
  color: var(--accent);
}

.totals-row {
  margin: 8px 0 12px;
}

.totals-bar {
  height: 6px;
  border-radius: 3px;
  background: var(--panel-border);
  overflow: hidden;
}

.totals-bar-fill {
  height: 100%;
  background: #4fa8ff;
  transition: width 0.3s ease;
}

.totals-text {
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-dim);
}

.legend-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.legend-item {
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.02em;
}

.source-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  font-size: 12px;
  border-top: 1px solid var(--panel-border);
}

.source-row:first-of-type {
  border-top: none;
}

.source-label {
  color: var(--text-dim);
  letter-spacing: 0.02em;
}

.source-stats {
  font-variant-numeric: tabular-nums;
  display: flex;
  gap: 8px;
}

.stat {
  font-weight: 600;
}

.stat--verified {
  color: #4fa8ff;
}

.stat--rejected {
  color: #c99;
}

.stat--pending {
  color: var(--text-dim);
}

.stat--pending-active {
  color: var(--accent);
}

.stat-total {
  color: var(--text-dim);
  margin-left: 4px;
}
</style>
