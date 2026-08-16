<script setup>
import { formatGB, formatExpiresIn } from '../format.js'

defineProps({
  models: { type: Array, default: () => [] },
})
</script>

<template>
  <section class="panel ollama-panel">
    <h3 class="panel-title">Ollama — Loaded Models</h3>

    <p v-if="!models.length" class="empty">no models currently loaded</p>

    <div class="model-row" v-for="m in models" :key="m.name">
      <div class="model-main">
        <span class="model-name">{{ m.name }}</span>
        <span class="model-spec">{{ m.parameter_size }} {{ m.quantization }}</span>
      </div>
      <div class="model-meta">
        <span>{{ formatGB(m.size_vram_bytes) }}</span>
        <span v-if="m.context_length">ctx {{ m.context_length.toLocaleString('en-US') }}</span>
        <span>TTL {{ formatExpiresIn(m.expires_at) }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ollama-panel {
  padding-bottom: 20px;
}

.empty {
  color: var(--text-dim);
  font-size: 12px;
  margin: 4px 0;
}

.model-row {
  padding: 8px 0;
  border-top: 1px solid var(--panel-border);
  font-size: 12px;
}

.model-row:first-of-type {
  border-top: none;
}

.model-main {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.model-name {
  color: var(--text);
}

.model-spec {
  color: var(--text-dim);
  white-space: nowrap;
}

.model-meta {
  display: flex;
  gap: 16px;
  margin-top: 3px;
  font-size: 10px;
  color: var(--text-dim);
  letter-spacing: 0.04em;
}
</style>
