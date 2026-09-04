<script setup>
const props = defineProps({
  bottleneck: { type: Object, default: null },
  ollamaActive: { type: Boolean, default: false },
})

function barClass(resource, current) {
  return resource === current ? 'bar--flagged' : 'bar--dim'
}
</script>

<template>
  <section class="panel bottleneck-panel">
    <h3 class="panel-title">Current Bottleneck</h3>

    <div class="row" v-for="r in ['GPU', 'CPU', 'RAM']" :key="r">
      <span class="label">{{ r }}</span>
      <div class="track">
        <div
          class="fill"
          :class="barClass(r, bottleneck?.resource)"
          :style="{ width: `${Math.min(100, (r === 'GPU' ? bottleneck?.gpu_pct : r === 'CPU' ? bottleneck?.cpu_pct : bottleneck?.ram_pct) ?? 0)}%` }"
        ></div>
      </div>
      <span class="value">
        {{ (r === 'GPU' ? bottleneck?.gpu_pct : r === 'CPU' ? bottleneck?.cpu_pct : bottleneck?.ram_pct) ?? '—' }}%
      </span>
    </div>

    <div class="row">
      <span class="label">LLM</span>
      <span class="llm-state">{{ ollamaActive ? '● ACTIVE' : '○ IDLE' }}</span>
    </div>

    <div class="verdict">
      BOTTLENECK: <strong>{{ bottleneck?.label || 'UNKNOWN' }}</strong>
    </div>
  </section>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 40px 1fr 48px;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  font-size: 12px;
}

.label {
  color: var(--text-dim);
}

.track {
  height: 8px;
  background: #0a0d0b;
  border: 1px solid var(--panel-border);
  overflow: hidden;
}

.fill {
  height: 100%;
}

.bar--flagged {
  background: var(--red);
}

.bar--dim {
  background: var(--accent-dim);
}

.value {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.llm-state {
  color: var(--accent);
  font-size: 11px;
}

.verdict {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--panel-border);
  font-size: 12px;
  letter-spacing: 0.04em;
}

.verdict strong {
  color: var(--red);
}
</style>
