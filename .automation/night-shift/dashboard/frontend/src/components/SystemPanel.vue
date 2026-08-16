<script setup>
import { computed } from 'vue'
import { formatGB, formatPercent } from '../format.js'

const props = defineProps({
  memory: { type: Object, default: null },
  cpu: { type: Object, default: null },
  gpu: { type: Object, default: null },
})

// Bar fill mirrors the used/total GB text exactly (psutil's own `percent`
// field is a "memory pressure" figure that nets out reclaimable cache —
// using it here would make the bar disagree with the GB numbers next to it).
const memoryPct = computed(() => {
  if (!props.memory?.total_bytes) return 0
  return (props.memory.used_bytes / props.memory.total_bytes) * 100
})
const gpuPct = computed(() => props.gpu?.device_utilization_pct ?? 0)

function barClass(pct) {
  if (pct >= 90) return 'bar--danger'
  if (pct >= 70) return 'bar--warn'
  return 'bar--ok'
}
</script>

<template>
  <section class="panel system-panel">
    <h3 class="panel-title">System</h3>

    <div class="row">
      <span class="row-label">Memory</span>
      <div class="row-bar-track">
        <div class="row-bar-fill" :class="barClass(memoryPct)" :style="{ width: `${Math.min(100, memoryPct)}%` }"></div>
      </div>
      <span class="row-value mono-num">
        <template v-if="memory">{{ formatGB(memory.used_bytes) }} / {{ formatGB(memory.total_bytes) }}</template>
        <template v-else>—</template>
      </span>
    </div>

    <div class="row">
      <span class="row-label">GPU</span>
      <div class="row-bar-track">
        <div class="row-bar-fill" :class="barClass(gpuPct)" :style="{ width: `${Math.min(100, gpuPct)}%` }"></div>
      </div>
      <span class="row-value mono-num">{{ gpu ? formatPercent(gpu.device_utilization_pct) : '—' }}</span>
    </div>
    <p class="row-sub" v-if="gpu">
      {{ gpu.model }}<template v-if="gpu.core_count">, {{ gpu.core_count }}-core</template>
      <template v-if="gpu.in_use_memory_bytes"> — {{ formatGB(gpu.in_use_memory_bytes) }} in use</template>
    </p>

    <div class="row">
      <span class="row-label">CPU</span>
      <div class="row-bar-track">
        <div class="row-bar-fill bar--ok" :style="{ width: `${Math.min(100, cpu?.percent ?? 0)}%` }"></div>
      </div>
      <span class="row-value mono-num">{{ cpu ? formatPercent(cpu.percent) : '—' }}</span>
    </div>
    <p class="row-sub" v-if="cpu?.load_avg_1m != null">
      load avg {{ cpu.load_avg_1m.toFixed(2) }} · {{ cpu.core_count }} cores
    </p>
  </section>
</template>

<style scoped>
.system-panel {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.row {
  display: grid;
  grid-template-columns: 64px 1fr 130px;
  align-items: center;
  gap: 12px;
  padding: 5px 0;
  font-size: 12px;
}

.row-label {
  color: var(--text-dim);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.row-bar-track {
  height: 8px;
  background: #0a0d0b;
  border: 1px solid var(--panel-border);
  overflow: hidden;
}

.row-bar-fill {
  height: 100%;
  transition: width 0.6s ease;
}

.bar--ok {
  background: var(--accent);
}

.bar--warn {
  background: var(--amber);
}

.bar--danger {
  background: var(--red);
}

.row-value {
  text-align: right;
  font-size: 12px;
}

.row-sub {
  margin: -2px 0 4px;
  padding-left: 76px;
  font-size: 10px;
  color: var(--text-dim);
}
</style>
