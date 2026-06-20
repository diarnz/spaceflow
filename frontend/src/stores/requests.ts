import { ref } from 'vue'
import { defineStore } from 'pinia'

import { requestsApi } from '@/api/client'
import type { EventRequestDetail, EventRequestSummary, PaginatedResponse } from '@/types'

export const useRequestsStore = defineStore('requests', () => {
  const list = ref<EventRequestSummary[]>([])
  const total = ref(0)
  const limit = ref(20)
  const offset = ref(0)
  const loading = ref(false)
  const active = ref<EventRequestDetail | null>(null)

  async function fetchList(params?: {
    status?: string
    venue_id?: string
    limit?: number
    offset?: number
  }) {
    loading.value = true
    try {
      const data: PaginatedResponse<EventRequestSummary> =
        await requestsApi.list(params)
      list.value = data.items
      total.value = data.total
      limit.value = data.limit
      offset.value = data.offset
      return data
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(requestId: string) {
    loading.value = true
    try {
      active.value = await requestsApi.get(requestId)
      return active.value
    } finally {
      loading.value = false
    }
  }

  return {
    list,
    total,
    limit,
    offset,
    loading,
    active,
    fetchList,
    fetchOne,
  }
})
