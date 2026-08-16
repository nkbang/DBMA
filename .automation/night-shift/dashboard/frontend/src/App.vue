<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import ProgressPanel from './components/ProgressPanel.vue'
import StatGrid from './components/StatGrid.vue'
import StatusPills from './components/StatusPills.vue'
import ThroughputChart from './components/ThroughputChart.vue'
import QueueList from './components/QueueList.vue'

const POLL_MS = 7000

const status = ref(null)
const monitorOnline = ref(null)
let timer = null

async function poll() {
  try {
    const res = await fetch('/api/status', { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    status.value = await res.json()
    monitorOnline.value = true
  } catch (e) {
    monitorOnline.value = false
  }
}

onMounted(() => {
  poll()
  timer = setInterval(poll, POLL_MS)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="dashboard">
    <header class="panel header">
      <h1>NAE NIGHT SHIFT</h1>
      <span class="live">
        <span class="dot" :class="monitorOnline ? 'dot--on' : 'dot--off'"></span>
        {{ monitorOnline ? 'LIVE' : 'RECONNECTING…' }}
      </span>
    </header>

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

    <StatusPills
      :process-alive="status?.process_alive ?? null"
      :ollama-online="status?.ollama_online ?? null"
      :monitor-online="monitorOnline"
    />

    <ThroughputChart :history="status?.throughput_history ?? []" />

    <QueueList
      :queue="status?.queue ?? []"
      :stopped="status?.queue_stopped ?? false"
      :stop-reason="status?.queue_stop_reason ?? null"
    />

    <footer class="panel footer">
      read-only monitor — no controls are sent to C1, Ollama, TSU, or Qdrant
    </footer>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header h1 {
  font-size: 15px;
  letter-spacing: 0.14em;
  margin: 0;
}

.live {
  display: flex;
  align-items: center;
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--text-dim);
}

.footer {
  text-align: center;
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.03em;
}
</style>
