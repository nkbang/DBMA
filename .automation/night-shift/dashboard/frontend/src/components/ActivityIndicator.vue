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
  gap: 10px;
  font-size: 12px;
  letter-spacing: 0.12em;
  font-weight: 700;
  padding: 6px 2px 2px;
  justify-content: center;
}
.txt { color: var(--text); }
.sub { color: var(--text-dim); letter-spacing: 0.04em; font-weight: 400; }

.tone-ok .txt { color: var(--accent); }
.tone-warn .txt { color: #e0a83a; }
.tone-bad .txt { color: #e5484d; }
.tone-dim .txt { color: var(--text-dim); }

.glyph {
  width: 16px;
  height: 16px;
  display: inline-block;
  flex: none;
  box-sizing: border-box;
  will-change: transform;
}

/* spinning ring — working / starting */
.glyph.spin {
  border: 3px solid rgba(255, 255, 255, 0.14);
  border-top-color: var(--accent);
  border-right-color: var(--accent);
  border-radius: 50%;
  animation: ai-spin 0.7s linear infinite;
}
@keyframes ai-spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

/* pulsing filled circle — stalled */
.glyph.pulse {
  background: #e0a83a;
  border-radius: 50%;
  box-shadow: 0 0 0 0 rgba(224, 168, 58, 0.6);
  animation: ai-pulse 1s ease-in-out infinite;
}
@keyframes ai-pulse {
  0% { transform: scale(0.75); box-shadow: 0 0 0 0 rgba(224, 168, 58, 0.55); }
  70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(224, 168, 58, 0); }
  100% { transform: scale(0.75); box-shadow: 0 0 0 0 rgba(224, 168, 58, 0); }
}

/* solid red circle — error (also blinks) */
.glyph.solid {
  background: #e5484d;
  border-radius: 50%;
  animation: ai-blink 0.9s steps(2, jump-none) infinite;
}
@keyframes ai-blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

/* red square — stopped */
.glyph.square { background: #e5484d; border-radius: 2px; }

/* dim dot — idle */
.glyph.dot { background: var(--text-dim); border-radius: 50%; transform: scale(0.55); }

@media (prefers-reduced-motion: reduce) {
  .glyph.spin, .glyph.pulse, .glyph.solid { animation-duration: 2s; }
}
</style>
