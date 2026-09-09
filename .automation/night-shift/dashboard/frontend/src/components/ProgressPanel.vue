<script setup>
import { computed } from 'vue'
import { formatCount, formatPercent } from '../format.js'

const props = defineProps({
  title: { type: String, default: null },
  processed: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  percentage: { type: Number, default: 0 },
  // Backend flag: an active run exists but has not written its first
  // tsu_report.json checkpoint yet (first checkpoint lands at candidate 100).
  awaitingFirstCheckpoint: { type: Boolean, default: false },
  // processed is extrapolated between checkpoints (raw number would sit flat
  // for ~16 min otherwise).
  isEstimate: { type: Boolean, default: false },
})

const starting = computed(() => props.awaitingFirstCheckpoint && props.processed === 0)
const barWidth = computed(() => `${Math.min(100, Math.max(0, props.percentage))}%`)
</script>

<template>
  <section class="panel progress-panel">
    <h2 class="volume-title">{{ title || 'WAITING FOR ACTIVE VOLUME…' }}</h2>

    <slot />

    <div class="bar-track">
      <div v-if="starting" class="bar-indeterminate"></div>
      <div v-else class="bar-fill" :class="{ 'bar-fill--est': isEstimate }" :style="{ width: barWidth }"></div>
      <span class="bar-label">{{ starting ? 'STARTING — awaiting first checkpoint' : (isEstimate ? '≈ ' : '') + formatPercent(percentage) }}</span>
    </div>

    <div class="counts">
      <span class="mono-num">{{ starting ? '—' : (isEstimate ? '≈ ' : '') + formatCount(processed) }}</span>
      <span class="counts-sep">/</span>
      <span class="mono-num counts-total">{{ total > 0 ? formatCount(total) : '—' }}</span>
    </div>
    <p v-if="isEstimate" class="est-note">estimated between checkpoints</p>
  </section>
</template>

<style scoped>
.progress-panel {
  text-align: center;
}

.volume-title {
  font-size: 15px;
  letter-spacing: 0.08em;
  margin: 0 0 10px;
  color: var(--text);
}

.bar-track {
  position: relative;
  height: 28px;
  background: #0a0d0b;
  border: 1px solid var(--panel-border);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-dim), var(--accent));
  transition: width 0.6s ease;
}

.bar-fill--est {
  background-image: linear-gradient(90deg, var(--accent-dim), var(--accent)),
    repeating-linear-gradient(45deg, rgba(0, 0, 0, 0.18) 0 6px, transparent 6px 12px);
}

.est-note {
  margin: 8px 0 0;
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--text-dim);
  text-transform: uppercase;
}

.bar-indeterminate {
  position: absolute;
  top: 0;
  left: -34%;
  height: 100%;
  width: 34%;
  background: linear-gradient(90deg, transparent, var(--accent-dim), transparent);
  animation: bar-sweep 1.4s ease-in-out infinite;
}

@keyframes bar-sweep {
  0% { left: -34%; }
  100% { left: 100%; }
}

.bar-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
}

.counts {
  margin-top: 18px;
  font-size: 32px;
  font-weight: 600;
}

.counts-sep {
  color: var(--text-dim);
  margin: 0 8px;
}

.counts-total {
  color: var(--text-dim);
}
</style>
