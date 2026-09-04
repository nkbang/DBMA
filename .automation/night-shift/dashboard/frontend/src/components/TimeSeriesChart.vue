<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  data: { type: Array, default: () => [] }, // [{t, value}]
  formatValue: { type: Function, default: (v) => `${Math.round(v)}` },
  emptyLabel: { type: String, default: 'collecting samples…' },
})

const VIEW_W = 600
const VIEW_H = 90
const PAD = 6

const points = computed(() => {
  const h = props.data
  if (!h || h.length < 2) return null

  const tMin = h[0].t
  const tMax = h[h.length - 1].t
  const tSpan = Math.max(tMax - tMin, 1)
  const rMax = Math.max(...h.map((s) => s.value), 1) * 1.15

  return h.map((s) => {
    const x = PAD + ((s.t - tMin) / tSpan) * (VIEW_W - PAD * 2)
    const y = VIEW_H - PAD - (s.value / rMax) * (VIEW_H - PAD * 2)
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

const latest = computed(() => {
  const h = props.data
  return h && h.length ? h[h.length - 1].value : null
})
</script>

<template>
  <div class="chart-block">
    <div class="chart-header">
      <span class="chart-title">{{ title }}</span>
      <span class="chart-latest" v-if="latest !== null">{{ formatValue(latest) }}</span>
    </div>
    <svg
      v-if="points"
      class="chart"
      :viewBox="`0 0 ${VIEW_W} ${VIEW_H}`"
      preserveAspectRatio="none"
    >
      <path :d="areaPath" class="chart-area" />
      <path :d="linePath" class="chart-line" />
    </svg>
    <p v-else class="chart-empty">{{ emptyLabel }}</p>
  </div>
</template>

<style scoped>
.chart-block {
  padding: 8px 0;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.chart-latest {
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

.chart {
  width: 100%;
  height: 56px;
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
  font-size: 11px;
  margin: 18px 0;
  text-align: center;
}
</style>
