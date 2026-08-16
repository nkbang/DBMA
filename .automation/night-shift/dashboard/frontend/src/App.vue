<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import ProgressPanel from './components/ProgressPanel.vue'
import StatGrid from './components/StatGrid.vue'
import HealthBar from './components/HealthBar.vue'
import PipelineFlow from './components/PipelineFlow.vue'
import SystemPanel from './components/SystemPanel.vue'
import GpuOperationsPanel from './components/GpuOperationsPanel.vue'
import BottleneckPanel from './components/BottleneckPanel.vue'
import TimeSeriesPanel from './components/TimeSeriesPanel.vue'
import QueueList from './components/QueueList.vue'
import EventLog from './components/EventLog.vue'
import { formatClockTime } from './format.js'

const REFRESH_OPTIONS = [5, 10, 30, 60]

const status = ref(null)
const monitorOnline = ref(null)
const monitoringEnabled = ref(true)
const refreshSeconds = ref(5)
const lastUpdateAt = ref(null)
let timer = null

async function poll() {
  try {
    const res = await fetch('/api/status', { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    status.value = await res.json()
    monitorOnline.value = true
    lastUpdateAt.value = Date.now() / 1000
  } catch (e) {
    monitorOnline.value = false
  }
}

function startTimer() {
  if (timer) clearInterval(timer)
  timer = setInterval(poll, refreshSeconds.value * 1000)
}

function toggleMonitoring() {
  monitoringEnabled.value = !monitoringEnabled.value
  if (monitoringEnabled.value) {
    poll()
    startTimer()
  } else if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function onRefreshChange() {
  if (monitoringEnabled.value) startTimer()
}

const nextUpdateAt = computed(() => {
  if (!monitoringEnabled.value || !lastUpdateAt.value) return null
  return lastUpdateAt.value + refreshSeconds.value
})

const pipelineRunning = computed(() => {
  const stages = status.value?.pipeline_stages || []
  return stages.length ? stages.some((s) => s.status === 'RUNNING') : null
})

onMounted(() => {
  poll()
  startTimer()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="dashboard">
    <header class="panel header">
      <div class="header-top">
        <div class="brand">
          <div class="brand-line">
            <span class="brand-title">내서재 작업현황모니터</span>
            <span class="brand-version">v1.0.0</span>
          </div>
          <div class="brand-line">
            <span class="brand-subtitle">NAE Observatory</span>
            <span class="brand-credit">제작총괄: d'Bang</span>
          </div>
        </div>
        <span class="live">
          <span class="dot" :class="!monitoringEnabled ? 'dot--unknown' : monitorOnline ? 'dot--on' : 'dot--off'"></span>
          {{ !monitoringEnabled ? 'PAUSED' : monitorOnline ? 'LIVE' : 'RECONNECTING…' }}
        </span>
      </div>
      <div class="header-controls">
        <label class="control">
          refresh
          <select v-model.number="refreshSeconds" @change="onRefreshChange">
            <option v-for="s in REFRESH_OPTIONS" :key="s" :value="s">{{ s }}s</option>
          </select>
        </label>
        <button class="toggle" @click="toggleMonitoring">
          {{ monitoringEnabled ? 'MONITOR: ON' : 'MONITOR: OFF' }}
        </button>
        <span class="updated">
          last {{ formatClockTime(lastUpdateAt) }} · next {{ formatClockTime(nextUpdateAt) }}
        </span>
      </div>
    </header>

    <HealthBar
      :process-alive="status?.process_alive ?? null"
      :pipeline-running="pipelineRunning"
      :ollama-online="status?.ollama_online ?? null"
      :gpu-health="status?.gpu_health?.status ?? null"
      :monitor-online="monitorOnline"
      :n8n-online="status?.n8n_online ?? null"
    />

    <ProgressPanel
      :title="status?.current_source?.title"
      :processed="status?.processed ?? 0"
      :total="status?.total ?? 0"
      :percentage="status?.percentage ?? 0"
    />

    <StatGrid
      :throughput-per-hour="status?.throughput_per_hour ?? null"
      :sec-per-item="status?.sec_per_item ?? null"
      :eta-seconds="status?.eta_seconds ?? null"
      :errors="status?.errors ?? 0"
    />

    <PipelineFlow :stages="status?.pipeline_stages ?? []" />

    <GpuOperationsPanel
      :gpu="status?.system?.gpu ?? null"
      :gpu-health="status?.gpu_health ?? null"
      :gpu-extended="status?.gpu_extended ?? null"
      :memory-total-bytes="status?.system?.memory?.total_bytes ?? null"
      :ollama-models="status?.ollama_models ?? []"
      :llama-parallelism="status?.llama_parallelism ?? []"
    />

    <BottleneckPanel :bottleneck="status?.bottleneck ?? null" :ollama-active="(status?.ollama_models ?? []).length > 0" />

    <SystemPanel
      :memory="status?.system?.memory ?? null"
      :cpu="status?.system?.cpu ?? null"
      :disk="status?.system?.disk ?? null"
      :disk-io-rate="status?.system?.disk_io_rate ?? null"
      :network-io-rate="status?.system?.network_io_rate ?? null"
    />

    <TimeSeriesPanel
      :throughput-history="status?.throughput_history ?? []"
      :latency-history="status?.latency_history ?? []"
      :gpu-history="status?.gpu_history ?? []"
      :vram-history="status?.vram_history ?? []"
      :ram-history="status?.ram_history ?? []"
      :cpu-history="status?.cpu_history ?? []"
    />

    <QueueList
      :queue="status?.queue ?? []"
      :stopped="status?.queue_stopped ?? false"
      :stop-reason="status?.queue_stop_reason ?? null"
    />

    <EventLog :events="status?.events ?? []" />

    <footer class="panel footer">
      read-only monitor — no controls are sent to C1, Ollama, TSU, or Qdrant.
      Pausing MONITOR only stops this dashboard's own polling; production keeps running either way.
    </footer>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brand-line {
  display: flex;
  align-items: baseline;
  gap: 16px;
}

.brand-title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.brand-subtitle {
  font-size: 11px;
  color: var(--text-dim);
  letter-spacing: 0.12em;
}

.brand-version {
  font-size: 11px;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
}

.brand-credit {
  font-size: 10px;
  color: var(--text-dim);
}

.live {
  display: flex;
  align-items: center;
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--text-dim);
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 11px;
  color: var(--text-dim);
  flex-wrap: wrap;
}

.control {
  display: flex;
  align-items: center;
  gap: 6px;
}

.control select {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--panel-border);
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 4px;
}

.toggle {
  background: var(--bg);
  color: var(--accent);
  border: 1px solid var(--accent-dim);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  padding: 3px 8px;
  cursor: pointer;
}

.toggle:hover {
  background: var(--panel-border);
}

.updated {
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}

.footer {
  text-align: center;
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.03em;
  line-height: 1.6;
}
</style>
