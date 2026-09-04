<script setup>
import { computed } from 'vue'
import { formatGB, formatPercent, formatBytesPerSec } from '../format.js'

const props = defineProps({
  memory: { type: Object, default: null },
  cpu: { type: Object, default: null },
  disk: { type: Object, default: null },
  diskIoRate: { type: Object, default: null },
  networkIoRate: { type: Object, default: null },
})

// Bar fill mirrors the used/total GB text exactly (psutil's own `percent`
// field is a "memory pressure" figure that nets out reclaimable cache —
// using it here would make the bar disagree with the GB numbers next to it).
const memoryPct = computed(() => {
  if (!props.memory?.total_bytes) return 0
  return (props.memory.used_bytes / props.memory.total_bytes) * 100
})

function barClass(pct) {
  if (pct >= 90) return 'bar--danger'
  if (pct >= 70) return 'bar--warn'
  return 'bar--ok'
}
</script>

<template>
  <section class="panel system-panel">
    <h3 class="panel-title">Resource</h3>

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
      <span class="row-label">CPU</span>
      <div class="row-bar-track">
        <div class="row-bar-fill bar--ok" :style="{ width: `${Math.min(100, cpu?.percent ?? 0)}%` }"></div>
      </div>
      <span class="row-value mono-num">{{ cpu ? formatPercent(cpu.percent) : '—' }}</span>
    </div>
    <p class="row-sub" v-if="cpu?.load_avg_1m != null">
      load avg {{ cpu.load_avg_1m.toFixed(2) }} · {{ cpu.core_count }} cores
    </p>

    <div class="row">
      <span class="row-label">Disk</span>
      <div class="row-bar-track">
        <div class="row-bar-fill bar--ok" :style="{ width: `${Math.min(100, disk?.percent ?? 0)}%` }"></div>
      </div>
      <span class="row-value mono-num">
        <template v-if="disk">{{ formatGB(disk.used_bytes) }} / {{ formatGB(disk.total_bytes) }}</template>
        <template v-else>—</template>
      </span>
    </div>
    <p class="row-sub" v-if="diskIoRate">
      read {{ formatBytesPerSec(diskIoRate.read_bytes_per_sec) }} · write {{ formatBytesPerSec(diskIoRate.write_bytes_per_sec) }}
    </p>

    <div class="row" v-if="networkIoRate">
      <span class="row-label">Network</span>
      <span class="row-value mono-num net-value">
        ↑ {{ formatBytesPerSec(networkIoRate.sent_bytes_per_sec) }} · ↓ {{ formatBytesPerSec(networkIoRate.recv_bytes_per_sec) }}
      </span>
    </div>
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

.net-value {
  grid-column: 2 / span 2;
}

.row-sub {
  margin: -2px 0 4px;
  padding-left: 76px;
  font-size: 10px;
  color: var(--text-dim);
}
</style>
