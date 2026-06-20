<script setup lang="ts">
import type { Conflict } from '@/types'

defineProps<{
  conflict: Conflict
}>()
</script>

<template>
  <div
    class="card"
    :style="{
      padding: '1rem 1.1rem',
      borderLeft: conflict.severity === 'blocking' ? '4px solid var(--error)' : '4px solid var(--warning)',
      background: conflict.severity === 'blocking' ? 'var(--error-light)' : 'var(--warning-light)',
    }"
  >
    <div style="display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-2);">
      <span class="badge" :class="conflict.severity === 'blocking' ? 'badge-error' : 'badge-warning'">
        {{ conflict.severity }}
      </span>
      <strong>{{ conflict.type ?? 'Operational conflict' }}</strong>
    </div>
    <p style="margin: 0 0 var(--space-2); color: var(--text-primary);">
      {{ conflict.description }}
    </p>
    <p style="margin: 0; color: var(--text-secondary);">
      <strong>Suggestion:</strong> {{ conflict.suggestion }}
    </p>
  </div>
</template>
