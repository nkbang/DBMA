<script setup>
defineProps({
  jobs: { type: Array, default: () => [] },
})

function badgeClass(status) {
  return {
    running: 'badge--running',
    complete: 'badge--complete',
    not_started: 'badge--queued',
  }[status] || 'badge--queued'
}

function badgeLabel(status) {
  return {
    running: 'RUNNING',
    complete: 'COMPLETE',
    not_started: 'NOT STARTED',
  }[status] || status.toUpperCase()
}
</script>

<template>
  <section class="panel cjk-panel" v-if="jobs.length">
    <h3 class="panel-title">CJK 표기 오류 복구</h3>

    <div class="cjk-row" v-for="job in jobs" :key="job.identifier">
      <div class="cjk-row-head">
        <span class="cjk-label">{{ job.identifier }}</span>
        <span class="badge" :class="badgeClass(job.status)">{{ badgeLabel(job.status) }}</span>
      </div>
      <div class="cjk-stats" v-if="job.report">
        candidates {{ job.report.candidates }} · repaired {{ job.report.repaired }} ·
        reextracted {{ job.report.reextracted }} · residual {{ job.report.residual }} ·
        failed {{ job.report.failed }} · {{ job.report.elapsed_seconds }}s
      </div>
    </div>
  </section>
</template>

<style scoped>
.cjk-panel {
  padding-bottom: 24px;
}

.cjk-row {
  padding: 6px 0;
  font-size: 12px;
  border-top: 1px solid var(--panel-border);
}

.cjk-row:first-of-type {
  border-top: none;
}

.cjk-row-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cjk-label {
  color: var(--text-dim);
  letter-spacing: 0.02em;
}

.cjk-stats {
  margin-top: 4px;
  color: var(--text-dim);
  font-size: 11px;
  opacity: 0.85;
}

.badge {
  font-size: 10px;
  letter-spacing: 0.06em;
}

.badge--running {
  color: var(--accent);
}

.badge--queued {
  color: var(--text-dim);
}

.badge--complete {
  color: #4fa8ff;
}
</style>
