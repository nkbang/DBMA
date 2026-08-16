<script setup>
import { computed } from 'vue'
import { formatGB, formatPercent, formatOrUnknown } from '../format.js'

const props = defineProps({
  gpu: { type: Object, default: null },
  gpuHealth: { type: Object, default: null },
  gpuExtended: { type: Object, default: null },
  memoryTotalBytes: { type: Number, default: null },
  ollamaModels: { type: Array, default: () => [] },
  llamaParallelism: { type: Array, default: () => [] },
})

const vramPct = computed(() => {
  if (!props.gpu?.in_use_memory_bytes || !props.memoryTotalBytes) return null
  return (props.gpu.in_use_memory_bytes / props.memoryTotalBytes) * 100
})

function healthBadge(status) {
  return {
    HEALTHY: { cls: 'badge--healthy', icon: '●', text: 'HEALTHY' },
    WARNING: { cls: 'badge--warning', icon: '⚠', text: 'WARNING' },
    ERROR: { cls: 'badge--error', icon: '🔴', text: 'ERROR' },
  }[status] || { cls: 'badge--unknown', icon: '●', text: 'UNKNOWN' }
}
</script>

<template>
  <section class="panel gpu-panel">
    <div class="header-row">
      <h3 class="panel-title">GPU Operations</h3>
      <span class="badge" :class="healthBadge(gpuHealth?.status).cls">
        {{ healthBadge(gpuHealth?.status).icon }} {{ healthBadge(gpuHealth?.status).text }}
      </span>
    </div>

    <p v-if="!gpu" class="empty">GPU telemetry unavailable this cycle</p>

    <div v-else class="grid">
      <div class="row"><span>Model</span><span>{{ gpu.model || '—' }} ({{ gpu.core_count }}-core)</span></div>
      <div class="row"><span>Utilization</span><span>{{ formatPercent(gpu.device_utilization_pct) }}</span></div>
      <div class="row">
        <span>VRAM</span>
        <span>{{ formatGB(gpu.in_use_memory_bytes) }} / {{ formatGB(memoryTotalBytes) }} (unified)</span>
      </div>
      <div class="row"><span>VRAM Usage</span><span>{{ vramPct !== null ? formatPercent(vramPct) : '—' }}</span></div>
      <div class="row"><span>Temperature</span><span>{{ formatOrUnknown(gpuExtended?.temperature_c, '°C') }}</span></div>
      <div class="row">
        <span>Power</span>
        <span>{{ formatOrUnknown(gpuExtended?.power_watts, ' W') }} / {{ formatOrUnknown(gpuExtended?.power_limit_watts, ' W') }}</span>
      </div>
      <div class="row"><span>GPU Clock</span><span>{{ formatOrUnknown(gpuExtended?.clock_mhz, ' MHz') }}</span></div>
      <div class="row"><span>Performance State</span><span>{{ formatOrUnknown(gpuExtended?.performance_state) }}</span></div>

      <div class="divider"></div>

      <div class="row"><span>Thermal Throttle</span><span>{{ gpuHealth?.thermal_throttle || 'UNKNOWN' }}</span></div>
      <div class="row"><span>Power Throttle</span><span>{{ gpuHealth?.power_throttle || 'UNKNOWN' }}</span></div>
      <div class="row">
        <span>XID Errors</span>
        <span>{{ gpuHealth?.xid_errors ?? 'N/A (Apple Silicon)' }}</span>
      </div>

      <div class="divider"></div>

      <div class="row"><span>Process</span><span>Ollama / llama-server</span></div>
      <div class="row">
        <span>Concurrency (-np)</span>
        <span>{{ llamaParallelism.length ? llamaParallelism.join(', ') : '—' }}</span>
      </div>
      <div class="row loaded-models">
        <span>Loaded</span>
        <span>
          <template v-if="ollamaModels.length">
            <span v-for="m in ollamaModels" :key="m.name" class="model-chip">{{ m.name }}</span>
          </template>
          <template v-else>none</template>
        </span>
      </div>
    </div>

    <p v-if="gpuHealth?.reason" class="reason">{{ gpuHealth.reason }}</p>
  </section>
</template>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.header-row .panel-title {
  margin: 0;
}

.badge {
  font-size: 11px;
  letter-spacing: 0.04em;
  padding: 2px 8px;
}

.badge--healthy {
  color: var(--bg);
  background: var(--accent);
}

.badge--warning {
  color: var(--bg);
  background: var(--amber);
}

.badge--error {
  color: #fff;
  background: var(--red);
}

.badge--unknown {
  color: var(--text-dim);
  border: 1px solid var(--gray);
}

.empty {
  color: var(--text-dim);
  font-size: 12px;
}

.grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.row > span:first-child {
  color: var(--text-dim);
}

.row > span:last-child {
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.divider {
  border-top: 1px solid var(--panel-border);
  margin: 4px 0;
}

.loaded-models span:last-child {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
}

.model-chip {
  border: 1px solid var(--panel-border);
  padding: 1px 6px;
  font-size: 10px;
}

.reason {
  margin: 10px 0 0;
  font-size: 10px;
  color: var(--text-dim);
}
</style>
