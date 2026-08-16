<script setup>
import { computed } from 'vue'

const props = defineProps({
  history: { type: Array, default: () => [] },
})

const VIEW_W = 600
const VIEW_H = 120
const PAD = 8

const points = computed(() => {
  const h = props.history
  if (!h || h.length < 2) return null

  const tMin = h[0].t
  const tMax = h[h.length - 1].t
  const tSpan = Math.max(tMax - tMin, 1)
  const rMax = Math.max(...h.map((s) => s.rate_per_hour), 1) * 1.15

  return h.map((s) => {
    const x = PAD + ((s.t - tMin) / tSpan) * (VIEW_W - PAD * 2)
    const y = VIEW_H - PAD - (s.rate_per_hour / rMax) * (VIEW_H - PAD * 2)
    return [x, y]
  })
})

const linePath = computed(() => {
  if (!points.value) return ''
  return points.value.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
})

const areaPath = computed(() => {
  if (!points.value) return ''
  const pts = points.value
  const first = pts[0]
  const last = pts[pts.length - 1]
  return `${linePath.value} L${last[0].toFixed(1)},${VIEW_H - PAD} L${first[0].toFixed(1)},${VIEW_H - PAD} Z`
})
</script>

<template>
  <section class="panel throughput-panel">
    <h3 class="panel-title">Throughput — Last 60 Minutes</h3>
    <svg
      v-if="points"
      class="chart"
      :viewBox="`0 0 ${VIEW_W} ${VIEW_H}`"
      preserveAspectRatio="none"
    >
      <path :d="areaPath" class="chart-area" />
      <path :d="linePath" class="chart-line" />
    </svg>
    <p v-else class="chart-empty">collecting throughput samples…</p>
  </section>
</template>

<style scoped>
.chart {
  width: 100%;
  height: 90px;
  display: block;
}

.chart-line {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}

.chart-area {
  fill: var(--accent);
  opacity: 0.12;
  stroke: none;
}

.chart-empty {
  color: var(--text-dim);
  font-size: 12px;
  margin: 24px 0;
  text-align: center;
}
</style>
