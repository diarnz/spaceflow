import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { assetsApi } from '@/api/client'
import type { Asset, AssetSummaryItem } from '@/types'

export const useAssetsStore = defineStore('assets', () => {
  const items = ref<Asset[]>([])
  const summary = ref<AssetSummaryItem[]>([])
  const loading = ref(false)

  const totalUnits = computed(() =>
    items.value.reduce((sum, item) => sum + item.total_quantity, 0),
  )

  async function fetchAll(category?: string) {
    loading.value = true
    try {
      items.value = await assetsApi.list(category)
      return items.value
    } finally {
      loading.value = false
    }
  }

  async function fetchSummary() {
    loading.value = true
    try {
      summary.value = await assetsApi.summary()
      return summary.value
    } finally {
      loading.value = false
    }
  }

  return {
    items,
    summary,
    loading,
    totalUnits,
    fetchAll,
    fetchSummary,
  }
})
