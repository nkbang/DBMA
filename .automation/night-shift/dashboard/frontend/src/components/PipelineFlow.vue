<script setup>
defineProps({
  stages: { type: Array, default: () => [] },
})

function badgeClass(status) {
  return {
    RUNNING: 'badge--running',
    COMPLETE: 'badge--complete',
    QUEUED: 'badge--queued',
    BLOCKED: 'badge--blocked',
    ERROR: 'badge--failed',
  }[status] || 'badge--queued'
}
</script>

<template>
  <section class="panel pipeline-panel">
    <h3 class="panel-title">Pipeline Status</h3>
    <p v-if="!stages.length" class="empty">no active volume</p>
    <div class="flow">
      <template v-for="(s, i) in stages" :key="s.stage">
        <div class="stage">
          <span class="stage-name">{{ s.stage }}</span>
          <span class="badge" :class="badgeClass(s.status)">{{ s.status }}</span>
        </div>
        <span v-if="i < stages.length - 1" class="arrow">→</span>
      </template>
    </div>
  </section>
</template>

<style scoped>
.pipeline-panel {
  overflow-x: auto;
}

.empty {
  color: var(--text-dim);
  font-size: 12px;
  margin: 4px 0;
}

.flow {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: max-content;
}

.stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 10px;
  border: 1px solid var(--panel-border);
  min-width: 84px;
}

.stage-name {
  font-size: 10px;
  color: var(--text-dim);
  text-align: center;
  white-space: nowrap;
}

.arrow {
  color: var(--panel-border);
  flex-shrink: 0;
}

.badge {
  font-size: 10px;
  letter-spacing: 0.04em;
  padding: 2px 6px;
}

.badge--running {
  color: var(--bg);
  background: var(--accent);
}

.badge--complete {
  color: var(--bg);
  background: #4fa8ff;
}

.badge--queued {
  color: var(--text-dim);
  border: 1px solid var(--gray);
}

.badge--blocked {
  color: var(--bg);
  background: var(--amber);
}

.badge--failed {
  color: var(--bg);
  background: var(--red);
}
</style>
