<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AppNav from '@/components/layout/AppNav.vue'
import RequestCard from '@/components/requests/RequestCard.vue'
import { friendlyError, requestsApi } from '@/api/client'
import type { EventRequestSummary } from '@/types'

const loading = ref(true)
const error = ref('')
const requests = ref<EventRequestSummary[]>([])
const statusFilter = ref('')

async function loadRequests() {
  loading.value = true
  error.value = ''
  try {
    const data = await requestsApi.list({
      status: statusFilter.value || undefined,
      limit: 50,
    })
    requests.value = data.items
  } catch (err) {
    error.value = friendlyError(err, 'Unable to load your requests.')
  } finally {
    loading.value = false
  }
}

onMounted(loadRequests)
</script>

<template>
  <div>
    <AppNav />

    <section style="padding: var(--space-10) 0 var(--space-12);">
      <div class="page-shell" style="display: grid; gap: var(--space-6);">
        <div style="display: flex; justify-content: space-between; align-items: center; gap: var(--space-4); flex-wrap: wrap;">
          <div>
            <h1 style="margin: 0 0 0.35rem;">My requests</h1>
            <p style="margin: 0; color: var(--text-secondary);">
              Track every event request you have submitted to SpaceFlow.
            </p>
          </div>
          <RouterLink to="/book" class="button button-primary">New request</RouterLink>
        </div>

        <div style="display: flex; gap: var(--space-3); flex-wrap: wrap;">
          <select v-model="statusFilter" class="input" style="width: auto; min-width: 180px;" @change="loadRequests">
            <option value="">All statuses</option>
            <option value="submitted">Submitted</option>
            <option value="under_review">Under review</option>
            <option value="quotation_sent">Quotation sent</option>
            <option value="approved">Approved</option>
            <option value="confirmed">Confirmed</option>
            <option value="rejected">Rejected</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <div v-if="error" class="card" style="padding: var(--space-4); color: var(--error); border-color: var(--error); background: var(--error-light);">
          {{ error }}
        </div>

        <div v-if="loading" style="color: var(--text-secondary);">Loading your requests...</div>

        <div v-else-if="!requests.length" class="card" style="padding: var(--space-8); text-align: center;">
          <h2 style="margin: 0 0 var(--space-3);">No requests yet</h2>
          <p style="margin: 0 0 var(--space-5); color: var(--text-secondary);">
            Start by booking a Pyramid space for your next event.
          </p>
          <RouterLink to="/book" class="button button-primary">Book a space</RouterLink>
        </div>

        <div v-else class="split-grid three-col">
          <RequestCard
            v-for="request in requests"
            :key="request.id"
            :request="request"
            :detail-path="`/my-requests/${request.id}`"
            :show-client="false"
          />
        </div>
      </div>
    </section>
  </div>
</template>
