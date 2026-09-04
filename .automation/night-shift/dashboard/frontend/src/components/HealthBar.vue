<script setup>
const props = defineProps({
  processAlive: { type: Boolean, default: null },
  pipelineRunning: { type: Boolean, default: null },
  ollamaOnline: { type: Boolean, default: null },
  gpuHealth: { type: String, default: null }, // 'HEALTHY' | 'WARNING' | 'ERROR' | 'UNKNOWN' | null
  monitorOnline: { type: Boolean, default: null },
  n8nOnline: { type: Boolean, default: null },
})

function boolItem(value, onLabel, offLabel) {
  if (value === null || value === undefined) return { cls: 'dot--unknown', label: `${onLabel} …` }
  return value ? { cls: 'dot--on', label: onLabel } : { cls: 'dot--off', label: offLabel }
}

function gpuItem(status) {
  if (status === 'HEALTHY') return { cls: 'dot--on', label: 'GPU HEALTHY' }
  if (status === 'WARNING') return { cls: 'dot--warn', label: 'GPU WARNING' }
  if (status === 'ERROR') return { cls: 'dot--off', label: 'GPU ERROR' }
  return { cls: 'dot--unknown', label: 'GPU UNKNOWN' }
}
</script>

<template>
  <section class="panel health-bar">
    <div class="item">
      <span class="dot" :class="boolItem(processAlive, '', '').cls"></span>
      {{ processAlive ? 'C1 RUNNING' : processAlive === false ? 'C1 STOPPED' : 'C1 …' }}
    </div>
    <div class="item">
      <span class="dot" :class="boolItem(pipelineRunning, '', '').cls"></span>
      {{ pipelineRunning ? 'TSU PIPELINE RUNNING' : pipelineRunning === false ? 'TSU PIPELINE IDLE' : 'TSU PIPELINE …' }}
    </div>
    <div class="item">
      <span class="dot" :class="boolItem(ollamaOnline, '', '').cls"></span>
      {{ ollamaOnline ? 'OLLAMA ONLINE' : ollamaOnline === false ? 'OLLAMA OFFLINE' : 'OLLAMA …' }}
    </div>
    <div class="item">
      <span class="dot" :class="gpuItem(gpuHealth).cls"></span>
      {{ gpuItem(gpuHealth).label }}
    </div>
    <div class="item">
      <span class="dot" :class="boolItem(monitorOnline, '', '').cls"></span>
      {{ monitorOnline ? 'MONITOR ONLINE' : 'MONITOR OFFLINE' }}
    </div>
    <div class="item">
      <span class="dot" :class="boolItem(n8nOnline, '', '').cls"></span>
      {{ n8nOnline ? 'N8N ONLINE' : n8nOnline === false ? 'N8N OFFLINE' : 'N8N …' }}
    </div>
  </section>
</template>

<style scoped>
.health-bar {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 16px;
  font-size: 11px;
}

.item {
  display: flex;
  align-items: center;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.dot--warn {
  background: var(--amber);
  box-shadow: 0 0 6px var(--amber);
}
</style>
