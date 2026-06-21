<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import EmptyState from '@/components/ui/EmptyState.vue'
import { friendlyError, requestsApi, tasksApi } from '@/api/client'
import { useNotificationsStore } from '@/stores/notifications'
import type { EventRequestSummary, TaskItem, TaskResponse, TaskStatus, User } from '@/types'

const notifications = useNotificationsStore()
const loading = ref(true)
const tasks = ref<TaskResponse[]>([])
const workers = ref<User[]>([])
const eventRequests = ref<EventRequestSummary[]>([])
const updatingTaskId = ref<string | null>(null)
const generating = ref(false)
const generationRequestId = ref('')
const selectedTask = ref<TaskResponse | null>(null)

const search = ref('')
const statusFilter = ref<'active' | TaskStatus | 'all'>('active')
const workerFilter = ref('all')

const editForm = reactive({
  assigned_to: '',
  pickup_room: '',
  destination_room: '',
  items: '',
  instructions: '',
  priority: 2,
})

const statusOptions: { key: TaskStatus; label: string }[] = [
  { key: 'pending', label: 'Pending' },
  { key: 'assigned', label: 'Assigned' },
  { key: 'in_progress', label: 'In progress' },
  { key: 'blocked', label: 'Blocked' },
  { key: 'done', label: 'Done' },
]

const priorityLabels: Record<number, string> = {
  1: 'Urgent',
  2: 'Normal',
  3: 'Low',
}

const now = computed(() => new Date())

const filteredTasks = computed(() => {
  const query = search.value.trim().toLowerCase()
  return [...tasks.value]
    .filter((task) => {
      if (statusFilter.value === 'active' && task.status === 'done') return false
      if (
        statusFilter.value !== 'active' &&
        statusFilter.value !== 'all' &&
        task.status !== statusFilter.value
      ) return false
      if (workerFilter.value === 'unassigned' && task.assigned_to) return false
      if (
        workerFilter.value !== 'all' &&
        workerFilter.value !== 'unassigned' &&
        task.assigned_to !== workerFilter.value
      ) return false
      if (!query) return true
      return [
        task.title,
        task.event_title,
        task.assignee_name,
        task.pickup_room,
        task.destination_room,
        task.items.map((item) => `${item.quantity} ${item.name}`).join(' '),
      ].some((value) => value?.toLowerCase().includes(query))
    })
    .sort((a, b) => {
      if (a.status === 'done' && b.status !== 'done') return 1
      if (a.status !== 'done' && b.status === 'done') return -1
      if (a.priority !== b.priority) return a.priority - b.priority
      return new Date(a.due_at).getTime() - new Date(b.due_at).getTime()
    })
})

const stats = computed(() => {
  const active = tasks.value.filter((task) => task.status !== 'done')
  return [
    { label: 'Active tasks', value: active.length, tone: 'info' },
    {
      label: 'Unassigned',
      value: active.filter((task) => !task.assigned_to).length,
      tone: 'warning',
    },
    {
      label: 'In progress',
      value: active.filter((task) => task.status === 'in_progress').length,
      tone: 'success',
    },
    {
      label: 'Blocked / overdue',
      value: active.filter((task) => task.status === 'blocked' || isOverdue(task)).length,
      tone: 'danger',
    },
  ]
})

const eligibleRequests = computed(() =>
  eventRequests.value
    .filter((request) => ['approved', 'confirmed'].includes(request.status))
    .sort((a, b) => a.requested_date.localeCompare(b.requested_date)),
)

function isOverdue(task: TaskResponse) {
  return task.status !== 'done' && new Date(task.due_at).getTime() < now.value.getTime()
}

function formatDue(task: TaskResponse) {
  const date = new Date(task.due_at)
  const today = new Date()
  const sameDay = date.toDateString() === today.toDateString()
  return `${sameDay ? 'Today' : date.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
}

function openDispatch(task: TaskResponse) {
  selectedTask.value = task
  editForm.assigned_to = task.assigned_to ?? ''
  editForm.pickup_room = task.pickup_room ?? ''
  editForm.destination_room = task.destination_room ?? ''
  editForm.items = task.items
    .map((item) => `${item.quantity} × ${item.name}`)
    .join(', ')
  editForm.instructions = task.instructions ?? task.description ?? ''
  editForm.priority = task.priority
}

function parseTaskItems(value: string): TaskItem[] {
  return value
    .split(',')
    .map((rawItem) => rawItem.trim())
    .filter(Boolean)
    .map((rawItem) => {
      const match = rawItem.match(/^(\d+)\s*(?:x|×)?\s+(.+)$/i)
      if (!match) return { name: rawItem, quantity: 1 }
      return {
        name: match[2].trim(),
        quantity: Math.max(1, Number(match[1])),
      }
    })
}

function replaceTask(updated: TaskResponse) {
  const index = tasks.value.findIndex((task) => task.id === updated.id)
  if (index >= 0) tasks.value[index] = updated
  if (selectedTask.value?.id === updated.id) selectedTask.value = updated
}

async function load() {
  loading.value = true
  try {
    const [taskData, workerData, requestData] = await Promise.all([
      tasksApi.list(),
      tasksApi.workers(),
      requestsApi.list({ limit: 100, offset: 0 }),
    ])
    tasks.value = taskData
    workers.value = workerData
    eventRequests.value = requestData.items
  } catch (err) {
    notifications.push(friendlyError(err, 'Unable to load operational tasks.'), 'error')
  } finally {
    loading.value = false
  }
}

async function generateDispatchPlan() {
  if (!generationRequestId.value) return
  generating.value = true
  try {
    const generated = await tasksApi.generate(generationRequestId.value)
    tasks.value = [
      ...tasks.value.filter((task) => task.event_request_id !== generationRequestId.value),
      ...generated,
    ]
    notifications.push(`${generated.length} operational dispatch tasks generated.`, 'success')
    generationRequestId.value = ''
  } catch (err) {
    notifications.push(friendlyError(err, 'Unable to generate the dispatch plan.'), 'error')
  } finally {
    generating.value = false
  }
}

async function updateTask(task: TaskResponse, payload: Parameters<typeof tasksApi.update>[1], successMessage: string) {
  updatingTaskId.value = task.id
  try {
    const updated = await tasksApi.update(task.id, payload)
    replaceTask(updated)
    notifications.push(successMessage, 'success')
  } catch (err) {
    notifications.push(friendlyError(err, 'Task update failed.'), 'error')
  } finally {
    updatingTaskId.value = null
  }
}

async function assignWorker(task: TaskResponse, workerId: string) {
  await updateTask(
    task,
    { assigned_to: workerId || null },
    workerId ? 'Worker assigned.' : 'Task returned to the unassigned queue.',
  )
}

async function moveTask(task: TaskResponse, nextStatus: TaskStatus) {
  await updateTask(task, { status: nextStatus }, `Task marked ${nextStatus.replaceAll('_', ' ')}.`)
}

async function saveDispatch() {
  if (!selectedTask.value) return
  const task = selectedTask.value
  await updateTask(
    task,
    {
      assigned_to: editForm.assigned_to || null,
      pickup_room: editForm.pickup_room.trim() || null,
      destination_room: editForm.destination_room.trim() || null,
      items: parseTaskItems(editForm.items),
      instructions: editForm.instructions.trim() || null,
      priority: editForm.priority,
    },
    'Dispatch instructions saved.',
  )
  selectedTask.value = null
}

onMounted(load)
</script>

<template>
  <section class="admin-page tasks-page">
    <div class="tasks-intro">
      <div>
        <p class="tasks-eyebrow">Live operations</p>
        <h2>Worker dispatch board</h2>
        <p class="admin-page-intro">
          Assign every move clearly: who is responsible, what they collect, where it comes
          from, and which room receives it.
        </p>
      </div>
      <button type="button" class="button button-secondary" :disabled="loading" @click="load">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M20 12a8 8 0 1 1-2.34-5.66M20 4v6h-6" />
        </svg>
        Refresh
      </button>
    </div>

    <div class="task-stats" aria-label="Task summary">
      <article v-for="stat in stats" :key="stat.label" class="task-stat" :class="`task-stat--${stat.tone}`">
        <span>{{ stat.label }}</span>
        <strong>{{ stat.value }}</strong>
      </article>
    </div>

    <section class="generator-panel" aria-labelledby="generator-title">
      <div>
        <p class="tasks-eyebrow">AI operations planner</p>
        <h3 id="generator-title">Generate a room-to-room dispatch plan</h3>
        <p>Select an approved event to create setup, logistics, preparation, and teardown tasks.</p>
      </div>
      <div class="generator-panel__actions">
        <label>
          <span class="sr-only">Approved event</span>
          <select v-model="generationRequestId" class="select">
            <option value="">Choose approved event…</option>
            <option v-for="request in eligibleRequests" :key="request.id" :value="request.id">
              {{ request.title }} · {{ request.venue_name || 'Room unassigned' }} · {{ request.requested_date }}
            </option>
          </select>
        </label>
        <button
          type="button"
          class="button button-primary"
          :disabled="!generationRequestId || generating"
          @click="generateDispatchPlan"
        >
          {{ generating ? 'Generating…' : 'Generate dispatch plan' }}
        </button>
      </div>
    </section>

    <div class="task-toolbar" aria-label="Task filters">
      <label class="task-search">
        <span class="sr-only">Search tasks</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path stroke-linecap="round" d="m20 20-3.5-3.5" />
        </svg>
        <input v-model="search" type="search" placeholder="Search task, room, item, or worker…" />
      </label>

      <label>
        <span class="sr-only">Filter by status</span>
        <select v-model="statusFilter" class="select">
          <option value="active">Active work</option>
          <option value="all">All statuses</option>
          <option v-for="status in statusOptions" :key="status.key" :value="status.key">
            {{ status.label }}
          </option>
        </select>
      </label>

      <label>
        <span class="sr-only">Filter by worker</span>
        <select v-model="workerFilter" class="select">
          <option value="all">All workers</option>
          <option value="unassigned">Unassigned only</option>
          <option v-for="worker in workers" :key="worker.id" :value="worker.id">
            {{ worker.full_name }}
          </option>
        </select>
      </label>
    </div>

    <EmptyState v-if="loading" title="Loading the dispatch board…" loading />

    <div v-else-if="filteredTasks.length" class="dispatch-list">
      <article
        v-for="task in filteredTasks"
        :key="task.id"
        class="dispatch-card"
        :class="{
          'is-overdue': isOverdue(task),
          'is-blocked': task.status === 'blocked',
          'is-done': task.status === 'done',
        }"
      >
        <div class="dispatch-card__rail" :class="`priority-${task.priority}`" />

        <div class="dispatch-card__main">
          <div class="dispatch-card__heading">
            <div class="dispatch-card__title">
              <div class="dispatch-card__badges">
                <span class="badge" :class="task.priority === 1 ? 'badge-error' : task.priority === 2 ? 'badge-warning' : 'badge-neutral'">
                  P{{ task.priority }} · {{ priorityLabels[task.priority] }}
                </span>
                <span class="badge badge-info">{{ task.task_type.replaceAll('_', ' ') }}</span>
                <span v-if="isOverdue(task)" class="badge badge-error">Overdue</span>
              </div>
              <h3>{{ task.title }}</h3>
              <p>{{ task.event_title || 'General venue operations' }}</p>
            </div>

            <button type="button" class="dispatch-edit" @click="openDispatch(task)">
              Edit dispatch
            </button>
          </div>

          <div class="route-strip" aria-label="Movement route">
            <div class="route-stop">
              <span class="route-stop__label">Collect from</span>
              <strong>{{ task.pickup_room || 'Pickup not set' }}</strong>
            </div>
            <div class="route-arrow" aria-hidden="true">
              <span />
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </div>
            <div class="route-stop route-stop--destination">
              <span class="route-stop__label">Deliver to</span>
              <strong>{{ task.destination_room || 'Destination not set' }}</strong>
            </div>
          </div>

          <div class="dispatch-card__details">
            <div class="detail-block">
              <span class="detail-block__label">Take / move</span>
              <div v-if="task.items.length" class="item-chips">
                <span v-for="item in task.items" :key="item.name">
                  <strong>{{ item.quantity }}×</strong>
                  {{ item.name }}
                </span>
              </div>
              <span v-else class="detail-empty">No items specified</span>
            </div>
            <div class="detail-block">
              <span class="detail-block__label">Worker instructions</span>
              <p>{{ task.instructions || 'Open Edit dispatch and add clear completion instructions.' }}</p>
            </div>
          </div>
        </div>

        <aside class="dispatch-card__controls">
          <div>
            <span class="control-label">Assigned worker</span>
            <select
              class="select"
              :disabled="updatingTaskId === task.id"
              :value="task.assigned_to ?? ''"
              @change="assignWorker(task, ($event.target as HTMLSelectElement).value)"
            >
              <option value="">Unassigned</option>
              <option v-for="worker in workers" :key="worker.id" :value="worker.id">
                {{ worker.full_name }}
              </option>
            </select>
          </div>

          <div>
            <span class="control-label">Due</span>
            <strong class="due-time" :class="{ 'due-time--late': isOverdue(task) }">
              {{ formatDue(task) }}
            </strong>
          </div>

          <div>
            <span class="control-label">Progress</span>
            <select
              class="select"
              :disabled="updatingTaskId === task.id"
              :value="task.status"
              @change="moveTask(task, ($event.target as HTMLSelectElement).value as TaskStatus)"
            >
              <option v-for="status in statusOptions" :key="status.key" :value="status.key">
                {{ status.label }}
              </option>
            </select>
          </div>
        </aside>
      </article>
    </div>

    <div v-else class="card tasks-empty">
      <EmptyState
        title="No tasks match these filters"
        message="Clear the filters or generate operational tasks from an approved request."
      />
    </div>

    <div v-if="selectedTask" class="dispatch-modal" role="presentation" @click.self="selectedTask = null">
      <section class="dispatch-sheet" role="dialog" aria-modal="true" aria-labelledby="dispatch-title">
        <div class="dispatch-sheet__head">
          <div>
            <p class="tasks-eyebrow">Dispatch instructions</p>
            <h2 id="dispatch-title">{{ selectedTask.title }}</h2>
            <p>{{ selectedTask.event_title }}</p>
          </div>
          <button type="button" class="sheet-close" aria-label="Close dispatch editor" @click="selectedTask = null">
            ×
          </button>
        </div>

        <div class="dispatch-form">
          <label class="field">
            <span>Assigned worker</span>
            <select v-model="editForm.assigned_to" class="select">
              <option value="">Unassigned</option>
              <option v-for="worker in workers" :key="worker.id" :value="worker.id">
                {{ worker.full_name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>Priority</span>
            <select v-model.number="editForm.priority" class="select">
              <option :value="1">P1 · Urgent</option>
              <option :value="2">P2 · Normal</option>
              <option :value="3">P3 · Low</option>
            </select>
          </label>

          <label class="field">
            <span>Collect from room</span>
            <input v-model="editForm.pickup_room" class="input" placeholder="e.g. Furniture Storage" />
          </label>

          <label class="field">
            <span>Deliver to room</span>
            <input v-model="editForm.destination_room" class="input" placeholder="e.g. Blue Room" />
          </label>

          <label class="field field--wide">
            <span>Items to take <small>Use quantity + item, separated by commas</small></span>
            <input v-model="editForm.items" class="input" placeholder="20 chairs, 4 tables, 1 projector" />
          </label>

          <label class="field field--wide">
            <span>Worker instructions</span>
            <textarea
              v-model="editForm.instructions"
              class="textarea"
              rows="5"
              placeholder="Explain placement, quantity checks, safety steps, and what confirms completion."
            />
          </label>
        </div>

        <div class="dispatch-sheet__actions">
          <button type="button" class="button button-secondary" @click="selectedTask = null">Cancel</button>
          <button
            type="button"
            class="button button-primary"
            :disabled="updatingTaskId === selectedTask.id"
            @click="saveDispatch"
          >
            {{ updatingTaskId === selectedTask.id ? 'Saving…' : 'Save dispatch' }}
          </button>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.tasks-page {
  --task-blue: #267fc2;
  --task-blue-soft: #eef7fd;
  --task-green: #168563;
  --task-amber: #ad6b0c;
  --task-red: #c54141;
}

.tasks-intro,
.dispatch-card__heading,
.dispatch-sheet__head,
.dispatch-sheet__actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.tasks-intro h2,
.dispatch-sheet h2 {
  margin: 0 0 var(--space-2);
  font-size: clamp(1.35rem, 2vw, 1.8rem);
  letter-spacing: -0.035em;
}

.tasks-eyebrow {
  margin: 0 0 var(--space-1);
  color: var(--task-blue);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.task-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3);
}

.task-stat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 78px;
  padding: var(--space-4);
  border: 1px solid var(--border);
  border-left: 4px solid var(--task-blue);
  border-radius: var(--radius-lg);
  background: var(--surface);
}

.task-stat span {
  color: var(--text-secondary);
  font-size: 0.84rem;
  font-weight: 650;
}

.task-stat strong {
  font-size: 1.7rem;
}

.task-stat--warning { border-left-color: var(--task-amber); }
.task-stat--success { border-left-color: var(--task-green); }
.task-stat--danger { border-left-color: var(--task-red); }

.task-toolbar {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 190px 210px;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
}

.generator-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  padding: var(--space-5);
  border: 1px solid rgba(38, 127, 194, 0.2);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, #f4faff, #eef7fd);
}

.generator-panel h3 {
  margin: 0 0 var(--space-1);
  font-size: 1.02rem;
}

.generator-panel p:not(.tasks-eyebrow) {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.88rem;
}

.generator-panel__actions {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) auto;
  gap: var(--space-3);
  min-width: min(100%, 560px);
}

.task-search {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  padding: 0 var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.task-search:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(61, 169, 245, 0.15);
}

.task-search svg {
  width: 19px;
  color: var(--text-tertiary);
}

.task-search input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
}

.dispatch-list {
  display: grid;
  gap: var(--space-4);
}

.dispatch-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 230px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}

.dispatch-card.is-overdue,
.dispatch-card.is-blocked {
  border-color: rgba(197, 65, 65, 0.35);
}

.dispatch-card.is-done {
  opacity: 0.72;
}

.dispatch-card__rail {
  position: absolute;
  inset: 0 auto 0 0;
  width: 5px;
  background: var(--task-amber);
}

.dispatch-card__rail.priority-1 { background: var(--task-red); }
.dispatch-card__rail.priority-3 { background: #8392a3; }

.dispatch-card__main {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
  padding-left: calc(var(--space-5) + 5px);
}

.dispatch-card__title h3 {
  margin: var(--space-2) 0 var(--space-1);
  font-size: 1.08rem;
  letter-spacing: -0.018em;
}

.dispatch-card__title p,
.dispatch-sheet__head p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.88rem;
}

.dispatch-card__badges,
.item-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.dispatch-edit {
  min-height: 44px;
  padding: 0 var(--space-3);
  border: 0;
  background: transparent;
  color: var(--task-blue);
  font-weight: 750;
  cursor: pointer;
}

.dispatch-edit:hover { text-decoration: underline; }

.route-strip {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 64px minmax(0, 1fr);
  align-items: stretch;
  border: 1px solid #d9e8f2;
  border-radius: var(--radius-md);
  background: var(--task-blue-soft);
}

.route-stop {
  display: grid;
  gap: 3px;
  padding: var(--space-3) var(--space-4);
}

.route-stop--destination {
  background: rgba(38, 127, 194, 0.07);
}

.route-stop__label,
.detail-block__label,
.control-label {
  color: var(--text-tertiary);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.route-arrow {
  display: flex;
  align-items: center;
  color: var(--task-blue);
}

.route-arrow span {
  width: 100%;
  height: 1px;
  background: currentColor;
}

.route-arrow svg {
  width: 22px;
  flex: 0 0 22px;
  margin-left: -4px;
}

.dispatch-card__details {
  display: grid;
  grid-template-columns: minmax(180px, 0.8fr) minmax(260px, 1.4fr);
  gap: var(--space-5);
}

.detail-block {
  display: grid;
  align-content: start;
  gap: var(--space-2);
}

.detail-block p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.55;
}

.item-chips span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  border-radius: var(--radius-full);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 0.8rem;
  font-weight: 650;
}

.item-chips strong {
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.detail-empty {
  color: var(--text-tertiary);
  font-size: 0.85rem;
}

.dispatch-card__controls {
  display: grid;
  align-content: center;
  gap: var(--space-4);
  padding: var(--space-5);
  border-left: 1px solid var(--border);
  background: var(--bg-secondary);
}

.dispatch-card__controls > div {
  display: grid;
  gap: var(--space-2);
}

.due-time {
  font-size: 0.92rem;
}

.due-time--late { color: var(--task-red); }

.tasks-empty {
  padding: var(--space-8);
}

.dispatch-modal {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  background: rgba(16, 29, 43, 0.52);
  backdrop-filter: blur(3px);
}

.dispatch-sheet {
  width: min(620px, 100%);
  height: 100%;
  overflow-y: auto;
  padding: var(--space-6);
  background: var(--surface);
  box-shadow: -18px 0 55px rgba(12, 34, 52, 0.2);
}

.dispatch-sheet__head {
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--border);
}

.sheet-close {
  width: 44px;
  height: 44px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 1.5rem;
  cursor: pointer;
}

.dispatch-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  padding: var(--space-6) 0;
}

.field {
  display: grid;
  gap: var(--space-2);
}

.field > span {
  font-size: 0.86rem;
  font-weight: 700;
}

.field small {
  margin-left: var(--space-2);
  color: var(--text-tertiary);
  font-weight: 500;
}

.field--wide { grid-column: 1 / -1; }

.textarea {
  width: 100%;
  resize: vertical;
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text-primary);
  font: inherit;
  line-height: 1.5;
}

.textarea:focus {
  outline: 0;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(61, 169, 245, 0.15);
}

.dispatch-sheet__actions {
  justify-content: flex-end;
  padding-top: var(--space-4);
  border-top: 1px solid var(--border);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 1050px) {
  .task-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .task-toolbar {
    grid-template-columns: 1fr 1fr;
  }

  .task-search {
    grid-column: 1 / -1;
  }

  .generator-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .dispatch-card {
    grid-template-columns: 1fr;
  }

  .dispatch-card__controls {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border-top: 1px solid var(--border);
    border-left: 0;
  }
}

@media (max-width: 700px) {
  .tasks-intro,
  .dispatch-card__heading {
    align-items: stretch;
    flex-direction: column;
  }

  .task-stats,
  .task-toolbar,
  .generator-panel__actions,
  .dispatch-form,
  .dispatch-card__details,
  .dispatch-card__controls {
    grid-template-columns: 1fr;
  }

  .task-search,
  .field--wide {
    grid-column: auto;
  }

  .route-strip {
    grid-template-columns: 1fr;
  }

  .route-arrow {
    min-height: 36px;
    justify-content: center;
    transform: rotate(90deg);
  }

  .route-arrow span { width: 40px; }
  .dispatch-card__main,
  .dispatch-card__controls { padding: var(--space-4); }
}
</style>
