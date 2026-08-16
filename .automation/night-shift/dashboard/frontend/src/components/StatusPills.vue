<script setup>
defineProps({
  processAlive: { type: Boolean, default: null },
  ollamaOnline: { type: Boolean, default: null },
  monitorOnline: { type: Boolean, default: null },
})

function dotClass(v) {
  if (v === null || v === undefined) return 'dot--unknown'
  return v ? 'dot--on' : 'dot--off'
}
</script>

<template>
  <section class="panel status-pills">
    <div class="pill">
      <span class="dot" :class="dotClass(processAlive)"></span>
      <span>{{ processAlive ? 'C1 PROCESSING' : 'C1 STOPPED' }}</span>
    </div>
    <div class="pill">
      <span class="dot" :class="dotClass(ollamaOnline)"></span>
      <span>{{ ollamaOnline ? 'OLLAMA ONLINE' : 'OLLAMA OFFLINE' }}</span>
    </div>
    <div class="pill">
      <span class="dot" :class="dotClass(monitorOnline)"></span>
      <span>{{ monitorOnline ? 'MONITOR ONLINE' : 'MONITOR OFFLINE' }}</span>
    </div>
  </section>
</template>

<style scoped>
.status-pills {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pill {
  display: flex;
  align-items: center;
  font-size: 13px;
  letter-spacing: 0.04em;
}
</style>
