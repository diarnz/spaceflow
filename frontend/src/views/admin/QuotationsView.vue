<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { friendlyError, quotationsApi, requestsApi } from '@/api/client'
import { useNotificationsStore } from '@/stores/notifications'
import type { EventRequestSummary, QuotationResponse } from '@/types'

const notifications = useNotificationsStore()
const requests = ref<EventRequestSummary[]>([])
const loading = ref(true)
const quotationByRequest = reactive<Record<string, QuotationResponse>>({})
const generatingFor = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    requests.value = (await requestsApi.list({ limit: 100, offset: 0 })).items
  } finally {
    loading.value = false
  }
}

async function generateQuotation(requestId: string) {
  generatingFor.value = requestId
  try {
    quotationByRequest[requestId] = await quotationsApi.generate(requestId)
    notifications.push('Quotation generated.', 'success')
  } catch (err) {
    notifications.push(friendlyError(err, 'Quotation generation failed.'), 'error')
  } finally {
    generatingFor.value = null
  }
}

async function sendQuotation(requestId: string) {
  const quotation = quotationByRequest[requestId]
  if (!quotation) return
  try {
    quotationByRequest[requestId] = await quotationsApi.send(quotation.id)
    notifications.push('Quotation marked as sent.', 'success')
  } catch (err) {
    notifications.push(friendlyError(err, 'Unable to send quotation.'), 'error')
  }
}

onMounted(load)
</script>

<template>
  <section class="card" style="padding: 0; overflow: hidden;">
    <div style="padding: var(--space-5); border-bottom: 1px solid var(--border);">
      <h2 style="margin: 0;">Quotations</h2>
      <p style="margin: var(--space-2) 0 0; color: var(--text-secondary);">
        Generate formal quotations from request data and AI-backed pricing logic.
      </p>
    </div>

    <div v-if="loading" class="empty-state">
      <div class="spinner" />
    </div>

    <table v-else style="width: 100%; border-collapse: collapse;">
      <thead>
        <tr style="background: var(--bg-secondary); text-align: left;">
          <th style="padding: 0.9rem 1rem;">Request</th>
          <th style="padding: 0.9rem 1rem;">Date</th>
          <th style="padding: 0.9rem 1rem;">Status</th>
          <th style="padding: 0.9rem 1rem;">Quotation</th>
          <th style="padding: 0.9rem 1rem;">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in requests"
          :key="item.id"
          style="border-top: 1px solid var(--border-light);"
        >
          <td style="padding: 1rem;">
            <div style="font-weight: 600;">{{ item.title }}</div>
            <div style="color: var(--text-tertiary); font-size: 0.85rem;">
              {{ item.attendee_count }} attendees
            </div>
          </td>
          <td style="padding: 1rem;">{{ item.requested_date }}</td>
          <td style="padding: 1rem;">{{ item.status }}</td>
          <td style="padding: 1rem;">
            <template v-if="quotationByRequest[item.id]">
              <strong>EUR {{ quotationByRequest[item.id].total_amount }}</strong>
              <div style="color: var(--text-tertiary); font-size: 0.82rem;">
                {{ quotationByRequest[item.id].status }}
              </div>
            </template>
            <span v-else style="color: var(--text-tertiary);">Not generated</span>
          </td>
          <td style="padding: 1rem;">
            <div style="display: flex; gap: var(--space-2); flex-wrap: wrap;">
              <button
                type="button"
                class="button button-secondary"
                :disabled="generatingFor === item.id"
                @click="generateQuotation(item.id)"
              >
                {{ generatingFor === item.id ? 'Generating...' : 'Generate' }}
              </button>
              <button
                v-if="quotationByRequest[item.id]"
                type="button"
                class="button button-primary"
                @click="sendQuotation(item.id)"
              >
                Send
              </button>
              <RouterLink
                :to="`/admin/requests/${item.id}`"
                class="button button-ghost"
              >
                Review
              </RouterLink>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
