<script setup lang="ts">
import { computed, onMounted } from 'vue'

import RequestCard from '@/components/requests/RequestCard.vue'
import { useAiStore } from '@/stores/ai'
import { useAssetsStore } from '@/stores/assets'
import { useRequestsStore } from '@/stores/requests'
import { useWebsocketStore } from '@/stores/websocket'

const ai = useAiStore()
const assets = useAssetsStore()
const requests = useRequestsStore()
const websocket = useWebsocketStore()

const recentRequests = computed(() => requests.list.slice(0, 5))
const approvedCount = computed(
  () => requests.list.filter((item) => item.status === 'approved').length,
)
const pendingCount = computed(
  () =>
    requests.list.filter((item) =>
      ['submitted', 'under_review', 'quotation_sent'].includes(item.status),
    ).length,
)

onMounted(async () => {
  await Promise.all([
    requests.fetchList({ limit: 20, offset: 0 }),
    assets.fetchAll(),
  ])
})
</script>

<template>
  <section style="display: grid; gap: var(--space-6);">
    <div class="split-grid four-col">
      <article class="card" style="padding: var(--space-5);">
        <div style="color: var(--text-tertiary); font-size: 0.82rem;">Total requests</div>
        <strong style="font-size: 2rem;">{{ requests.total }}</strong>
      </article>
      <article class="card" style="padding: var(--space-5);">
        <div style="color: var(--text-tertiary); font-size: 0.82rem;">Pending review</div>
        <strong style="font-size: 2rem;">{{ pendingCount }}</strong>
      </article>
      <article class="card" style="padding: var(--space-5);">
        <div style="color: var(--text-tertiary); font-size: 0.82rem;">Approved</div>
        <strong style="font-size: 2rem;">{{ approvedCount }}</strong>
      </article>
      <article class="card" style="padding: var(--space-5);">
        <div style="color: var(--text-tertiary); font-size: 0.82rem;">Asset units tracked</div>
        <strong style="font-size: 2rem;">{{ assets.totalUnits }}</strong>
      </article>
    </div>

    <div class="split-grid two-col">
      <div style="display: grid; gap: var(--space-4);">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <h2 style="margin: 0;">Recent requests</h2>
          <RouterLink to="/admin/requests" class="button button-secondary">
            View all
          </RouterLink>
        </div>

        <div v-if="requests.loading" class="empty-state">
          <div class="spinner" />
        </div>
        <div v-else style="display: grid; gap: var(--space-3);">
          <RequestCard
            v-for="item in recentRequests"
            :key="item.id"
            :request="item"
          />
          <div v-if="!recentRequests.length" class="empty-state">
            No requests yet.
          </div>
        </div>
      </div>

      <div style="display: grid; gap: var(--space-4);">
        <h2 style="margin: 0;">Quick actions</h2>
        <div class="card" style="padding: var(--space-5); display: grid; gap: var(--space-3);">
          <RouterLink to="/book" class="button button-secondary">New booking request</RouterLink>
          <RouterLink to="/admin/inventory" class="button button-secondary">Open inventory</RouterLink>
          <RouterLink to="/admin/calendar" class="button button-secondary">View calendar</RouterLink>
          <RouterLink to="/admin/visualization" class="button button-secondary">Open 3D view</RouterLink>
          <button
            type="button"
            class="button button-primary"
            @click="ai.setPanelState(true, 'copilot', {})"
          >
            Ask AI copilot
          </button>
        </div>

        <div class="card" style="padding: var(--space-5); display: grid; gap: var(--space-3);">
          <h3 style="margin: 0;">Realtime status</h3>
          <div style="display: flex; align-items: center; gap: var(--space-2); color: var(--text-secondary);">
            <span
              :style="{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: websocket.connected ? 'var(--success)' : 'var(--warning)',
                display: 'inline-block',
              }"
            />
            {{ websocket.connected ? 'Admin websocket connected' : 'Admin websocket reconnecting' }}
          </div>
          <div style="color: var(--text-tertiary); font-size: 0.88rem;">
            Active 3D bridge connections: {{ websocket.active3dConnections }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
