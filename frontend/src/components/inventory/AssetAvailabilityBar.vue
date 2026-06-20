<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  available: number
  total: number
}>()

const percent = computed(() => {
  if (props.total <= 0) return 0
  return Math.max(0, Math.min(100, (props.available / props.total) * 100))
})

const color = computed(() => {
  if (percent.value > 60) return 'var(--success)'
  if (percent.value > 30) return 'var(--warning)'
  return 'var(--error)'
})
</script>

<template>
  <div style="display: flex; align-items: center; gap: var(--space-3);">
    <div
      style="
        position: relative;
        flex: 1;
        height: 8px;
        border-radius: var(--radius-full);
        background: var(--bg-tertiary);
        overflow: hidden;
      "
    >
      <div
        :style="{
          width: `${percent}%`,
          height: '100%',
          background: color,
        }"
      />
    </div>
    <span style="font-size: 0.82rem; color: var(--text-secondary); min-width: 62px; text-align: right;">
      {{ available }}/{{ total }}
    </span>
  </div>
</template>
