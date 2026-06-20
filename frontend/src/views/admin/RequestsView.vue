<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import RequestCard from '@/components/requests/RequestCard.vue'
import { useRequestsStore } from '@/stores/requests'

const requests = useRequestsStore()

const selectedStatus = ref('')
const search = ref('')

const filteredRequests = computed(() => {
  const query = search.value.trim().toLowerCase()
  return requests.list.filter((item) => {
    const statusMatch = !selectedStatus.value || item.status === selectedStatus.value
    if (!statusMatch) return false
    if (!query) return true
    return (
      item.title.toLowerCase().includes(query) ||
      (item.client_name ?? '').toLowerCase().includes(query) ||
      (item.venue_name ?? '').toLowerCase().includes(query)
    )
  })
})

async function load() {
  await requests.fetchList({
    status: selectedStatus.value || undefined,
    limit: 100,
    offset: 0,
  })
}

watch(selectedStatus, () => {
  load()
})

onMounted(load)
</script>

<template>
  <section style="display: grid; gap: var(--space-5);">
    <div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--space-4);">
      <div style="display: flex; flex-wrap: wrap; gap: var(--space-2);">
        <button
          type="button"
          class="button"
          :class="selectedStatus === '' ? 'button-primary' : 'button-secondary'"
          @click="selectedStatus = ''"
        >
          All
        </button>
        <button
          v-for="status in ['submitted', 'under_review', 'quotation_sent', 'approved', 'completed', 'rejected']"
          :key="status"
          type="button"
          class="button"
          :class="selectedStatus === status ? 'button-primary' : 'button-secondary'"
          @click="selectedStatus = status"
        >
          {{ status.replace('_', ' ') }}
        </button>
      </div>

      <input
        v-model="search"
        class="input"
        placeholder="Search by title, client, or venue..."
        style="max-width: 320px;"
      />
    </div>

    <div v-if="requests.loading" class="empty-state">
      <div class="spinner" />
    </div>

    <div v-else-if="!filteredRequests.length" class="empty-state">
      No requests match the current filters.
    </div>

    <div v-else style="display: grid; gap: var(--space-3);">
      <RequestCard
        v-for="item in filteredRequests"
        :key="item.id"
        :request="item"
      />
    </div>
  </section>
</template>
