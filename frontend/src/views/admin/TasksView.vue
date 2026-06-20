<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { friendlyError, tasksApi } from '@/api/client'
import { useNotificationsStore } from '@/stores/notifications'
import type { TaskResponse, TaskStatus } from '@/types'

const notifications = useNotificationsStore()
const loading = ref(true)
const tasks = ref<TaskResponse[]>([])
const updatingTaskId = ref<string | null>(null)

const columns: { key: TaskStatus; label: string }[] = [
  { key: 'pending', label: 'Pending' },
  { key: 'assigned', label: 'Assigned' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'done', label: 'Done' },
  { key: 'blocked', label: 'Blocked' },
]

const grouped = computed(() =>
  Object.fromEntries(
    columns.map((column) => [
      column.key,
      tasks.value.filter((task) => task.status === column.key),
    ]),
  ) as Record<TaskStatus, TaskResponse[]>,
)

async function load() {
  loading.value = true
  try {
    tasks.value = await tasksApi.list()
  } finally {
    loading.value = false
  }
}

async function moveTask(task: TaskResponse, nextStatus: TaskStatus) {
  updatingTaskId.value = task.id
  try {
    const updated = await tasksApi.update(task.id, { status: nextStatus })
    const index = tasks.value.findIndex((item) => item.id === task.id)
    if (index >= 0) tasks.value[index] = updated
    notifications.push('Task updated.', 'success')
  } catch (err) {
    notifications.push(friendlyError(err, 'Task update failed.'), 'error')
  } finally {
    updatingTaskId.value = null
  }
}

onMounted(load)
</script>

<template>
  <section v-if="loading" class="empty-state">
    <div class="spinner" />
  </section>

  <section v-else class="split-grid" style="grid-template-columns: repeat(5, minmax(0, 1fr)); align-items: start;">
    <article
      v-for="column in columns"
      :key="column.key"
      class="card"
      style="padding: var(--space-4); display: grid; gap: var(--space-3); background: var(--bg-secondary);"
    >
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <strong>{{ column.label }}</strong>
        <span class="badge badge-neutral">{{ grouped[column.key].length }}</span>
      </div>

      <div v-if="!grouped[column.key].length" style="color: var(--text-tertiary); font-size: 0.85rem;">
        No tasks here.
      </div>

      <article
        v-for="task in grouped[column.key]"
        :key="task.id"
        class="card"
        style="padding: var(--space-4); display: grid; gap: var(--space-3);"
      >
        <div style="display: flex; justify-content: space-between; gap: var(--space-2);">
          <span class="badge badge-info">{{ task.task_type }}</span>
          <span class="badge" :class="task.ai_generated ? 'badge-success' : 'badge-neutral'">
            {{ task.ai_generated ? 'AI' : 'Manual' }}
          </span>
        </div>

        <div>
          <strong>{{ task.title }}</strong>
          <div style="color: var(--text-secondary); margin-top: 0.25rem; font-size: 0.9rem;">
            {{ task.event_title || 'No event title' }}
          </div>
        </div>

        <div style="color: var(--text-tertiary); font-size: 0.85rem;">
          Due {{ new Date(task.due_at).toLocaleString() }}
        </div>

        <select
          class="select"
          :disabled="updatingTaskId === task.id"
          :value="task.status"
          @change="moveTask(task, ($event.target as HTMLSelectElement).value as TaskStatus)"
        >
          <option v-for="option in columns" :key="option.key" :value="option.key">
            {{ option.label }}
          </option>
        </select>
      </article>
    </article>
  </section>
</template>
