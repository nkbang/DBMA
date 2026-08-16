<script setup>
import { formatClockTime } from '../format.js'

defineProps({
  events: { type: Array, default: () => [] },
})

function levelClass(level) {
  return { info: 'level--info', warn: 'level--warn', error: 'level--error' }[level] || 'level--info'
}
</script>

<template>
  <section class="panel event-panel">
    <h3 class="panel-title">Events</h3>
    <p v-if="!events.length" class="empty">no events yet — this fills in as checkpoints/transitions happen</p>
    <div class="row" v-for="(e, i) in events" :key="i">
      <span class="time mono-num">{{ formatClockTime(e.ts) }}</span>
      <span class="dot" :class="levelClass(e.level) === 'level--error' ? 'dot--off' : levelClass(e.level) === 'level--warn' ? 'dot--warn' : 'dot--on'"></span>
      <span class="message" :class="levelClass(e.level)">{{ e.message }}</span>
    </div>
  </section>
</template>

<style scoped>
.event-panel {
  max-height: 260px;
  overflow-y: auto;
}

.empty {
  color: var(--text-dim);
  font-size: 12px;
}

.row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 4px 0;
  font-size: 11px;
}

.time {
  color: var(--text-dim);
  flex-shrink: 0;
}

.message {
  overflow-wrap: anywhere;
}

.level--error {
  color: var(--red);
}

.level--warn {
  color: var(--amber);
}

.dot--warn {
  background: var(--amber);
  box-shadow: 0 0 6px var(--amber);
}
</style>
