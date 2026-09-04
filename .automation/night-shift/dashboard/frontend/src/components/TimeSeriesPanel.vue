<script setup>
import { computed } from 'vue'
import TimeSeriesChart from './TimeSeriesChart.vue'

const props = defineProps({
  throughputHistory: { type: Array, default: () => [] },
  latencyHistory: { type: Array, default: () => [] },
  gpuHistory: { type: Array, default: () => [] },
  vramHistory: { type: Array, default: () => [] },
  ramHistory: { type: Array, default: () => [] },
  cpuHistory: { type: Array, default: () => [] },
})

const throughputSeries = computed(() => props.throughputHistory.map((s) => ({ t: s.t, value: s.rate_per_hour })))
const latencySeries = computed(() => props.latencyHistory.map((s) => ({ t: s.t, value: s.sec_per_item })))
</script>

<template>
  <section class="panel timeseries-panel">
    <h3 class="panel-title">Time Series — Last 60 Minutes</h3>
    <div class="grid">
      <TimeSeriesChart title="Throughput" :data="throughputSeries" :format-value="(v) => `${Math.round(v)}/h`" />
      <TimeSeriesChart title="Latency" :data="latencySeries" :format-value="(v) => `${v.toFixed(1)}s/item`" />
      <TimeSeriesChart title="GPU Utilization" :data="gpuHistory" :format-value="(v) => `${Math.round(v)}%`" />
      <TimeSeriesChart title="VRAM" :data="vramHistory" :format-value="(v) => `${(v / 1e9).toFixed(1)}GB`" />
      <TimeSeriesChart title="RAM" :data="ramHistory" :format-value="(v) => `${Math.round(v)}%`" />
      <TimeSeriesChart title="CPU" :data="cpuHistory" :format-value="(v) => `${Math.round(v)}%`" />
    </div>
  </section>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 24px;
}

@media (max-width: 520px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
