<script setup lang="ts">
import { useRouter } from 'vue-router'

import RequestStatusBadge from './RequestStatusBadge.vue'
import type { EventRequestSummary } from '@/types'

const props = withDefaults(
  defineProps<{
    request: EventRequestSummary
    detailPath?: string
    showClient?: boolean
  }>(),
  {
    detailPath: '',
    showClient: true,
  },
)

const router = useRouter()

function openDetail() {
  const path = props.detailPath || `/admin/requests/${props.request.id}`
  router.push(path)
}
</script>

<template>
  <article
    class="card"
    style="padding: var(--space-5); cursor: pointer;"
    @click="openDetail"
  >
    <div
      style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--space-3);
        margin-bottom: var(--space-3);
      "
    >
      <RequestStatusBadge :status="request.status" />
      <span style="font-size: 0.82rem; color: var(--text-tertiary);">
        {{ request.requested_date }}
      </span>
    </div>

    <h3 style="margin: 0 0 var(--space-2); font-size: 1.05rem;">
      {{ request.title }}
    </h3>
    <p style="margin: 0 0 var(--space-3); color: var(--text-secondary);">
      {{ request.event_type }} · {{ request.attendee_count }} attendees
    </p>

    <div style="display: flex; flex-wrap: wrap; gap: var(--space-3); color: var(--text-tertiary); font-size: 0.85rem;">
      <span v-if="showClient && request.client_name">Client: {{ request.client_name }}</span>
      <span v-if="request.venue_name">Venue: {{ request.venue_name }}</span>
    </div>

    <div style="margin-top: var(--space-4); display: flex; align-items: center; justify-content: space-between;">
      <span
        class="badge"
        :class="request.has_conflicts ? 'badge-warning' : request.has_ai_proposal ? 'badge-success' : 'badge-neutral'"
      >
        {{
          request.has_conflicts
            ? 'AI flagged conflicts'
            : request.has_ai_proposal
              ? 'AI proposal ready'
              : 'AI analysis pending'
        }}
      </span>

      <button type="button" class="button button-secondary" style="padding: 0.45rem 0.8rem;">
        Review
      </button>
    </div>
  </article>
</template>
