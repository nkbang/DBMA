<script setup>
import { computed } from 'vue'
import { formatCount, formatPercent } from '../format.js'

const props = defineProps({
  title: { type: String, default: null },
  processed: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  percentage: { type: Number, default: 0 },
})

const barWidth = computed(() => `${Math.min(100, Math.max(0, props.percentage))}%`)
</script>

<template>
  <section class="panel progress-panel">
    <h2 class="volume-title">{{ title || 'WAITING FOR ACTIVE VOLUME…' }}</h2>

    <div class="bar-track">
      <div class="bar-fill" :style="{ width: barWidth }"></div>
      <span class="bar-label">{{ formatPercent(percentage) }}</span>
    </div>

    <div class="counts">
      <span class="mono-num">{{ formatCount(processed) }}</span>
      <span class="counts-sep">/</span>
      <span class="mono-num counts-total">{{ formatCount(total) }}</span>
    </div>
  </section>
</template>

<style scoped>
.progress-panel {
  text-align: center;
}

.volume-title {
  font-size: 15px;
  letter-spacing: 0.08em;
  margin: 0 0 20px;
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
