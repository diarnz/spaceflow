<script setup lang="ts">
import type { AiMessage } from '@/types'

defineProps<{
  message: AiMessage
}>()

function formatTime(timestamp: string) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div
    :style="{
      display: 'flex',
      justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
      marginBottom: '1rem',
    }"
  >
    <div
      :style="{
        maxWidth: '85%',
        background: message.role === 'user' ? 'var(--accent)' : 'var(--surface)',
        color: message.role === 'user' ? '#fff' : 'var(--text-primary)',
        border: message.role === 'user' ? 'none' : '1px solid var(--border)',
        borderRadius: '16px',
        padding: '0.9rem 1rem',
        boxShadow: message.role === 'user' ? 'none' : 'var(--shadow-sm)',
      }"
    >
      <div style="white-space: pre-wrap; line-height: 1.6;">
        {{ message.content }}
      </div>

      <div
        v-if="message.toolCalls?.length"
        style="display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.75rem;"
      >
        <span
          v-for="tool in message.toolCalls"
          :key="tool.tool"
          class="badge badge-neutral"
          style="text-transform: none; letter-spacing: 0;"
        >
          {{ tool.tool }}
        </span>
      </div>

      <div
        :style="{
          marginTop: '0.55rem',
          fontSize: '0.75rem',
          color: message.role === 'user' ? 'rgba(255,255,255,0.78)' : 'var(--text-tertiary)',
          textAlign: message.role === 'user' ? 'right' : 'left',
        }"
      >
        {{ formatTime(message.timestamp) }}
      </div>
    </div>
  </div>
</template>
