<script setup>
import { computed } from 'vue'

const props = defineProps({
  // idle | starting | working | stalled | stopped | error
  activity: { type: String, default: 'idle' },
  reportAgeSeconds: { type: Number, default: null },
})

const MAP = {
  working: { label: 'PROCESSING', kind: 'spin', tone: 'ok' },
  starting: { label: 'STARTING', kind: 'spin', tone: 'ok' },
  stalled: { label: 'STALLED', kind: 'pulse', tone: 'warn' },
  error: { label: 'LLM ERRORS', kind: 'solid', tone: 'bad' },
  stopped: { label: 'STOPPED', kind: 'square', tone: 'bad' },
  idle: { label: 'IDLE', kind: 'dot', tone: 'dim' },
}

const view = computed(() => MAP[props.activity] || MAP.idle)

const sub = computed(() => {
  if (props.activity === 'stalled' && props.reportAgeSeconds != null) {
    const m = Math.floor(props.reportAgeSeconds / 60)
    return m >= 1 ? `no checkpoint for ${m}m` : 'no recent checkpoint'
  }
  if (props.activity === 'stalled') return 'first checkpoint overdue'
  return null
})
</script>

<template>
  <div class="activity" :class="`tone-${view.tone}`" role="status" :aria-label="view.label">
    <span class="glyph" :class="view.kind"></span>
    <span class="txt">{{ view.label }}</span>
    <span v-if="sub" class="sub">· {{ sub }}</span>
  </div>
</template>

<style scoped>
.activity {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  letter-spacing: 0.12em;
  font-weight: 600;
  padding: 6px 2px 0;
  justify-content: center;
}
.txt { color: var(--text); }
.sub { color: var(--text-dim); letter-spacing: 0.04em; font-weight: 400; }

.tone-ok .txt { color: var(--accent); }
.tone-warn .txt { color: #e0a83a; }
.tone-bad .txt { color: #e5484d; }
.tone-dim .txt { color: var(--text-dim); }

.glyph { width: 12px; height: 12px; display: inline-block; flex: none; }

/* spinning ring — working / starting */
.glyph.spin {
  border: 2px solid var(--accent-dim);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* pulsing filled circle — stalled */
.glyph.pulse {
  background: #e0a83a;
  border-radius: 50%;
  animation: pulse 1s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.35; transform: scale(0.7); } }

/* solid red circle — error */
.glyph.solid { background: #e5484d; border-radius: 50%; }

/* red square — stopped */
.glyph.square { background: #e5484d; }

/* dim dot — idle */
.glyph.dot { background: var(--text-dim); border-radius: 50%; transform: scale(0.6); }
</style>
