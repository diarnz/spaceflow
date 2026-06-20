<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import AiProposalCard from '@/components/requests/AiProposalCard.vue'
import ConflictAlert from '@/components/requests/ConflictAlert.vue'
import RequestStatusBadge from '@/components/requests/RequestStatusBadge.vue'
import ThreeDFrame from '@/components/visualization/ThreeDFrame.vue'
import {
  aiApi,
  friendlyError,
  requestsApi,
  reservationsApi,
  tasksApi,
} from '@/api/client'
import { useAiStore } from '@/stores/ai'
import { useNotificationsStore } from '@/stores/notifications'
import { useRequestsStore } from '@/stores/requests'
import type { Conflict, ReservationResponse, TaskResponse } from '@/types'

const route = useRoute()
const requestStore = useRequestsStore()
const notifications = useNotificationsStore()
const ai = useAiStore()

const activeTab = ref<'overview' | 'conflicts' | 'tasks' | 'reservations' | 'room'>('overview')
const conflicts = ref<Conflict[]>([])
const tasks = ref<TaskResponse[]>([])
const reservations = ref<ReservationResponse[]>([])
const rejectReason = ref('')
const showReject = ref(false)
const actioning = ref(false)
const loadingExtras = ref(false)

const requestId = computed(() => String(route.params.id))
const requestDetail = computed(() => requestStore.active)
const hasRequest = computed(() => Boolean(requestDetail.value))

async function loadDetail() {
  await requestStore.fetchOne(requestId.value)
  await loadExtras()
}

async function loadExtras() {
  loadingExtras.value = true
  try {
    const [conflictData, taskData, reservationData] = await Promise.all([
      requestsApi.conflicts(requestId.value).catch(() => ({
        conflicts: [],
      })),
      tasksApi.list({ request_id: requestId.value }).catch(() => []),
      reservationsApi.list(requestId.value).catch(() => []),
    ])
    conflicts.value = conflictData.conflicts ?? []
    tasks.value = taskData
    reservations.value = reservationData
  } finally {
    loadingExtras.value = false
  }
}

async function approve() {
  actioning.value = true
  try {
    await requestsApi.approve(requestId.value)
    notifications.push('Request approved.', 'success')
    await loadDetail()
  } catch (err) {
    notifications.push(friendlyError(err, 'Approval failed.'), 'error')
  } finally {
    actioning.value = false
  }
}

async function reject() {
  if (!rejectReason.value.trim()) return
  actioning.value = true
  try {
    await requestsApi.reject(requestId.value, rejectReason.value)
    notifications.push('Request rejected.', 'warning')
    showReject.value = false
    rejectReason.value = ''
    await loadDetail()
  } catch (err) {
    notifications.push(friendlyError(err, 'Rejection failed.'), 'error')
  } finally {
    actioning.value = false
  }
}

async function generateTasks() {
  actioning.value = true
  try {
    tasks.value = await tasksApi.generate(requestId.value)
    notifications.push('Tasks generated.', 'success')
  } catch (err) {
    notifications.push(friendlyError(err, 'Task generation failed.'), 'error')
  } finally {
    actioning.value = false
  }
}

async function runConflictAgent() {
  actioning.value = true
  try {
    const result = await aiApi.detectConflicts(requestId.value)
    conflicts.value = result.conflicts ?? conflicts.value
    notifications.push('Conflict analysis completed.', 'success')
  } catch (err) {
    notifications.push(friendlyError(err, 'Conflict analysis failed.'), 'error')
  } finally {
    actioning.value = false
  }
}

function openAi(mode: 'copilot' | 'room_designer' | 'planner' | 'conflict_detector') {
  ai.resetConversation()
  ai.setPanelState(true, mode, {
    request_id: requestId.value,
    venue_name: requestDetail.value?.venue?.name,
    event_request_id: requestId.value,
  })
}

onMounted(loadDetail)
</script>

<template>
  <section v-if="requestStore.loading && !hasRequest" class="empty-state">
    <div class="spinner" />
  </section>

  <section v-else-if="!requestDetail" class="empty-state">
    Request not found.
  </section>

  <section v-else style="display: grid; gap: var(--space-6);">
    <header class="card" style="padding: var(--space-6); display: grid; gap: var(--space-4);">
      <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap;">
        <div>
          <RouterLink to="/admin/requests" style="color: var(--text-tertiary); font-size: 0.9rem;">
            ← Back to requests
          </RouterLink>
          <h1 style="margin: var(--space-2) 0;">{{ requestDetail.title }}</h1>
          <div style="display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap;">
            <RequestStatusBadge :status="requestDetail.status" />
            <span style="color: var(--text-secondary);">
              {{ requestDetail.event_type }} · {{ requestDetail.attendee_count }} attendees · {{ requestDetail.requested_date }}
            </span>
          </div>
        </div>

        <div style="display: flex; gap: var(--space-2); flex-wrap: wrap;">
          <button type="button" class="button button-secondary" @click="openAi('copilot')">
            Ask AI
          </button>
          <button
            v-if="['submitted', 'under_review', 'quotation_sent'].includes(requestDetail.status)"
            type="button"
            class="button button-primary"
            :disabled="actioning"
            @click="approve"
          >
            Approve
          </button>
          <button
            v-if="!['rejected', 'completed', 'cancelled'].includes(requestDetail.status)"
            type="button"
            class="button button-danger"
            :disabled="actioning"
            @click="showReject = true"
          >
            Reject
          </button>
        </div>
      </div>

      <div style="display: flex; gap: var(--space-2); flex-wrap: wrap;">
        <button
          type="button"
          class="button"
          :class="activeTab === 'overview' ? 'button-primary' : 'button-secondary'"
          @click="activeTab = 'overview'"
        >
          Overview
        </button>
        <button
          type="button"
          class="button"
          :class="activeTab === 'conflicts' ? 'button-primary' : 'button-secondary'"
          @click="activeTab = 'conflicts'"
        >
          Conflicts
        </button>
        <button
          type="button"
          class="button"
          :class="activeTab === 'reservations' ? 'button-primary' : 'button-secondary'"
          @click="activeTab = 'reservations'"
        >
          Reservations
        </button>
        <button
          type="button"
          class="button"
          :class="activeTab === 'tasks' ? 'button-primary' : 'button-secondary'"
          @click="activeTab = 'tasks'"
        >
          Tasks
        </button>
        <button
          type="button"
          class="button"
          :class="activeTab === 'room' ? 'button-primary' : 'button-secondary'"
          @click="activeTab = 'room'"
        >
          3D Room
        </button>
      </div>
    </header>

    <div v-if="activeTab === 'overview'" class="split-grid two-col">
      <article class="card" style="padding: var(--space-6); display: grid; gap: var(--space-3);">
        <h2 style="margin: 0;">Request details</h2>
        <div><strong>Client:</strong> {{ requestDetail.client?.full_name ?? 'Unknown' }}</div>
        <div><strong>Organization:</strong> {{ requestDetail.client?.organization ?? 'N/A' }}</div>
        <div><strong>Venue:</strong> {{ requestDetail.venue?.name ?? 'Not assigned' }}</div>
        <div><strong>Time:</strong> {{ requestDetail.start_time }} - {{ requestDetail.end_time }}</div>
        <div><strong>Setup / teardown:</strong> {{ requestDetail.setup_time_minutes }} / {{ requestDetail.teardown_time_minutes }} mins</div>
        <div><strong>Requirements:</strong> {{ requestDetail.special_requirements || 'None' }}</div>
        <div v-if="requestDetail.description"><strong>Description:</strong> {{ requestDetail.description }}</div>
      </article>

      <AiProposalCard
        v-if="requestDetail.ai_proposal_json"
        :proposal="requestDetail.ai_proposal_json"
      />
      <div v-else class="card" style="padding: var(--space-6);">
        <div style="display: flex; align-items: center; gap: var(--space-3);">
          <div class="spinner" />
          <span>AI proposal is still being prepared.</span>
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'conflicts'" style="display: grid; gap: var(--space-4);">
      <div style="display: flex; justify-content: space-between; align-items: center; gap: var(--space-3);">
        <h2 style="margin: 0;">Conflict detection</h2>
        <button type="button" class="button button-secondary" :disabled="actioning" @click="runConflictAgent">
          Run AI conflict check
        </button>
      </div>

      <div v-if="loadingExtras && !conflicts.length" class="empty-state">
        <div class="spinner" />
      </div>

      <div v-else-if="!conflicts.length" class="card" style="padding: var(--space-6); color: var(--success);">
        No conflicts detected for this request.
      </div>

      <ConflictAlert
        v-for="(conflict, index) in conflicts"
        :key="index"
        :conflict="conflict"
      />
    </div>

    <div v-else-if="activeTab === 'reservations'" class="card" style="padding: var(--space-6);">
      <h2 style="margin-top: 0;">Asset reservations</h2>

      <div v-if="loadingExtras && !reservations.length" class="empty-state">
        <div class="spinner" />
      </div>

      <div v-else-if="!reservations.length" class="empty-state">
        No asset reservations yet.
      </div>

      <div v-else style="display: grid; gap: var(--space-3);">
        <div
          v-for="reservation in reservations"
          :key="reservation.id"
          class="card"
          style="padding: var(--space-4); display: flex; align-items: center; justify-content: space-between; gap: var(--space-4);"
        >
          <div>
            <strong>{{ reservation.asset_name }}</strong>
            <div style="color: var(--text-secondary);">
              Requested {{ reservation.quantity_requested }} · confirmed {{ reservation.quantity_confirmed }}
            </div>
          </div>
          <span class="badge badge-neutral">{{ reservation.status }}</span>
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'tasks'" style="display: grid; gap: var(--space-4);">
      <div style="display: flex; justify-content: space-between; align-items: center; gap: var(--space-3);">
        <h2 style="margin: 0;">Operational tasks</h2>
        <button
          type="button"
          class="button button-primary"
          :disabled="actioning"
          @click="generateTasks"
        >
          Generate task list
        </button>
      </div>

      <div v-if="loadingExtras && !tasks.length" class="empty-state">
        <div class="spinner" />
      </div>

      <div v-else-if="!tasks.length" class="card" style="padding: var(--space-6); color: var(--text-secondary);">
        No tasks have been generated for this request yet.
      </div>

      <div v-else style="display: grid; gap: var(--space-3);">
        <article
          v-for="task in tasks"
          :key="task.id"
          class="card"
          style="padding: var(--space-4); display: flex; justify-content: space-between; align-items: center; gap: var(--space-4);"
        >
          <div>
            <div style="display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1);">
              <span class="badge badge-neutral">{{ task.task_type }}</span>
              <span class="badge" :class="task.status === 'done' ? 'badge-success' : task.status === 'blocked' ? 'badge-error' : 'badge-info'">
                {{ task.status }}
              </span>
            </div>
            <strong>{{ task.title }}</strong>
            <div style="color: var(--text-secondary); margin-top: 0.25rem;">
              Due {{ new Date(task.due_at).toLocaleString() }}
            </div>
          </div>
          <div style="text-align: right;">
            <div style="color: var(--text-tertiary); font-size: 0.82rem;">Priority</div>
            <strong>{{ task.priority }}</strong>
          </div>
        </article>
      </div>
    </div>

    <div v-else-if="activeTab === 'room'" style="display: grid; gap: var(--space-4);">
      <div style="display: flex; justify-content: space-between; align-items: center; gap: var(--space-3);">
        <h2 style="margin: 0;">3D room visualization</h2>
        <button
          type="button"
          class="button button-primary"
          @click="openAi('room_designer')"
        >
          Design with AI
        </button>
      </div>
      <ThreeDFrame :room-id="requestDetail.venue?.three_d_room_id" />
    </div>

    <div v-if="showReject" class="modal-backdrop">
      <div class="modal-card">
        <div class="modal-header">
          <strong>Reject request</strong>
          <button type="button" class="button button-ghost" @click="showReject = false">×</button>
        </div>
        <div class="modal-body">
          <label class="field">
            <span class="field-label">Reason</span>
            <textarea
              v-model="rejectReason"
              class="textarea"
              rows="4"
              placeholder="Explain why this request is being rejected."
            />
          </label>
        </div>
        <div class="modal-footer">
          <button type="button" class="button button-secondary" @click="showReject = false">
            Cancel
          </button>
          <button type="button" class="button button-danger" :disabled="actioning" @click="reject">
            Confirm rejection
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
