<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppNav from '@/components/layout/AppNav.vue'
import RequestStatusBadge from '@/components/requests/RequestStatusBadge.vue'
import { friendlyError, requestsApi } from '@/api/client'
import type { EventRequestDetail } from '@/types'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const request = ref<EventRequestDetail | null>(null)

const aiSummary = computed(() => {
  const proposal = request.value?.ai_proposal_json
  if (!proposal || typeof proposal !== 'object') return null
  const text = (proposal as Record<string, unknown>).summary
  return typeof text === 'string' ? text : null
})

onMounted(async () => {
  try {
    request.value = await requestsApi.get(String(route.params.id))
  } catch (err) {
    error.value = friendlyError(err, 'Unable to load this request.')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <AppNav />

    <section style="padding: var(--space-10) 0 var(--space-12);">
      <div class="page-shell" style="display: grid; gap: var(--space-6);">
        <button type="button" class="button button-secondary" style="width: fit-content;" @click="router.push('/my-requests')">
          Back to my requests
        </button>

        <div v-if="loading" style="color: var(--text-secondary);">Loading request...</div>

        <div v-else-if="error" class="card" style="padding: var(--space-4); color: var(--error); border-color: var(--error); background: var(--error-light);">
          {{ error }}
        </div>

        <template v-else-if="request">
          <div style="display: flex; justify-content: space-between; align-items: start; gap: var(--space-4); flex-wrap: wrap;">
            <div>
              <RequestStatusBadge :status="request.status" />
              <h1 style="margin: var(--space-3) 0;">{{ request.title }}</h1>
              <p style="margin: 0; color: var(--text-secondary);">
                {{ request.event_type }} · {{ request.attendee_count }} attendees
              </p>
            </div>
          </div>

          <div class="split-grid two-col">
            <section class="card" style="padding: var(--space-6); display: grid; gap: var(--space-4);">
              <h2 style="margin: 0;">Event details</h2>
              <div><strong>Date:</strong> {{ request.requested_date }}</div>
              <div><strong>Time:</strong> {{ request.start_time }} – {{ request.end_time }}</div>
              <div><strong>Venue:</strong> {{ request.venue?.name || 'To be assigned' }}</div>
              <div v-if="request.description"><strong>Description:</strong> {{ request.description }}</div>
              <div v-if="request.special_requirements"><strong>Special requirements:</strong> {{ request.special_requirements }}</div>
              <div v-if="request.rejection_reason" style="color: var(--error);">
                <strong>Rejection reason:</strong> {{ request.rejection_reason }}
              </div>
            </section>

            <section class="card" style="padding: var(--space-6); display: grid; gap: var(--space-4);">
              <h2 style="margin: 0;">Review progress</h2>
              <p style="margin: 0; color: var(--text-secondary);">
                Your request moves through AI analysis, staff review, quotation, and final confirmation.
              </p>
              <div class="badge badge-neutral">Submitted {{ new Date(request.created_at).toLocaleString() }}</div>
              <div v-if="aiSummary" class="card" style="padding: var(--space-4); background: var(--bg-secondary);">
                <strong>AI summary</strong>
                <p style="margin: var(--space-2) 0 0;">{{ aiSummary }}</p>
              </div>
              <div v-else style="color: var(--text-tertiary);">
                AI analysis will appear here once processing completes.
              </div>
            </section>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>
