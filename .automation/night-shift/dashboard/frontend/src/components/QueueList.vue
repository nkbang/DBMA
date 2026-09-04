<script setup>
import { volumeLabel } from '../format.js'

defineProps({
  queue: { type: Array, default: () => [] },
  stopped: { type: Boolean, default: false },
  stopReason: { type: String, default: null },
})

function badgeClass(status) {
  return {
    RUNNING: 'badge--running',
    QUEUED: 'badge--queued',
    COMPLETE: 'badge--complete',
    FAILED: 'badge--failed',
  }[status] || 'badge--queued'
}
</script>

<template>
  <section class="panel queue-panel">
    <h3 class="panel-title">NAE Queue</h3>

    <p v-if="stopped" class="stop-banner">
      QUEUE STOPPED{{ stopReason ? ` — ${stopReason}` : '' }}
    </p>

    <div class="queue-row" v-for="item in queue" :key="item.identifier">
      <span class="queue-label">{{ volumeLabel(item.identifier) }}</span>
      <div class="queue-bar-track">
        <div
          class="queue-bar-fill"
          :class="badgeClass(item.status)"
          :style="{ width: `${Math.min(100, Math.max(0, item.progress_pct))}%` }"
        ></div>
      </div>
      <span class="badge" :class="badgeClass(item.status)">{{ item.status }}</span>
    </div>
  </section>
</template>

<style scoped>
.queue-panel {
  padding-bottom: 24px;
}

.stop-banner {
  color: var(--red);
  font-size: 12px;
  margin: -4px 0 14px;
}

.queue-row {
  display: grid;
  grid-template-columns: 56px 1fr 84px;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  font-size: 12px;
}

.queue-label {
  color: var(--text-dim);
  letter-spacing: 0.04em;
}

.queue-bar-track {
  height: 8px;
  background: #0a0d0b;
  border: 1px solid var(--panel-border);
  overflow: hidden;
}

.queue-bar-fill {
  height: 100%;
}

.badge {
  text-align: right;
  font-size: 10px;
  letter-spacing: 0.06em;
}

.badge--running,
.queue-bar-fill.badge--running {
  color: var(--accent);
  background: var(--accent);
}
span.badge--running {
  background: none;
  color: var(--accent);
}

.badge--queued,
.queue-bar-fill.badge--queued {
  background: var(--gray);
}
span.badge--queued {
  background: none;
  color: var(--text-dim);
}

.badge--complete,
.queue-bar-fill.badge--complete {
  background: #4fa8ff;
}
span.badge--complete {
  background: none;
  color: #4fa8ff;
}

.badge--failed,
.queue-bar-fill.badge--failed {
  background: var(--red);
}
span.badge--failed {
  background: none;
  color: var(--red);
}
</style>
