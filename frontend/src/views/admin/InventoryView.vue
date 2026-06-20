<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AssetAvailabilityBar from '@/components/inventory/AssetAvailabilityBar.vue'
import { useAssetsStore } from '@/stores/assets'

const assets = useAssetsStore()
const category = ref('')

const categories = [
  { value: '', label: 'All' },
  { value: 'seating', label: 'Seating' },
  { value: 'tables', label: 'Tables' },
  { value: 'av_equipment', label: 'AV Equipment' },
  { value: 'staging', label: 'Staging' },
  { value: 'lighting', label: 'Lighting' },
  { value: 'misc', label: 'Misc' },
]

const filteredItems = computed(() =>
  category.value
    ? assets.items.filter((item) => item.category === category.value)
    : assets.items,
)

onMounted(async () => {
  await Promise.all([assets.fetchAll(), assets.fetchSummary()])
})
</script>

<template>
  <section style="display: grid; gap: var(--space-6);">
    <div class="split-grid four-col">
      <article class="card" style="padding: var(--space-5);">
        <div style="color: var(--text-tertiary); font-size: 0.82rem;">Asset types</div>
        <strong style="font-size: 2rem;">{{ assets.items.length }}</strong>
      </article>
      <article class="card" style="padding: var(--space-5);">
        <div style="color: var(--text-tertiary); font-size: 0.82rem;">Units tracked</div>
        <strong style="font-size: 2rem;">{{ assets.totalUnits }}</strong>
      </article>
      <article class="card" style="padding: var(--space-5);">
        <div style="color: var(--text-tertiary); font-size: 0.82rem;">Conflict risk next 7 days</div>
        <strong style="font-size: 2rem;">
          {{ assets.summary.filter((item) => item.has_conflict_next_7_days).length }}
        </strong>
      </article>
      <article class="card" style="padding: var(--space-5);">
        <div style="color: var(--text-tertiary); font-size: 0.82rem;">3D-linked assets</div>
        <strong style="font-size: 2rem;">
          {{ assets.items.filter((item) => item.three_d_item_key).length }}
        </strong>
      </article>
    </div>

    <div style="display: flex; flex-wrap: wrap; gap: var(--space-2);">
      <button
        v-for="item in categories"
        :key="item.value"
        type="button"
        class="button"
        :class="category === item.value ? 'button-primary' : 'button-secondary'"
        @click="category = item.value"
      >
        {{ item.label }}
      </button>
    </div>

    <div v-if="assets.loading" class="empty-state">
      <div class="spinner" />
    </div>

    <div v-else class="split-grid three-col">
      <article
        v-for="asset in filteredItems"
        :key="asset.id"
        class="card"
        style="padding: var(--space-5); display: grid; gap: var(--space-4);"
      >
        <div style="display: flex; justify-content: space-between; gap: var(--space-3);">
          <div>
            <h3 style="margin: 0 0 var(--space-1); font-size: 1rem;">{{ asset.name }}</h3>
            <div style="color: var(--text-secondary);">{{ asset.category }}</div>
          </div>
          <span class="badge badge-neutral">{{ asset.tracking_type }}</span>
        </div>

        <div>
          <div style="font-size: 2rem; font-weight: 700;">{{ asset.total_quantity }}</div>
          <div style="color: var(--text-tertiary);">units in pool</div>
        </div>

        <AssetAvailabilityBar
          :available="assets.summary.find((item) => item.asset_id === asset.id)?.available_quantity ?? asset.total_quantity"
          :total="asset.total_quantity"
        />

        <div style="display: flex; justify-content: space-between; align-items: center; color: var(--text-secondary); font-size: 0.9rem;">
          <span>EUR {{ asset.unit_price }} / unit</span>
          <span v-if="asset.three_d_item_key" class="badge badge-info">
            3D: {{ asset.three_d_item_key }}
          </span>
        </div>
      </article>
    </div>
  </section>
</template>
