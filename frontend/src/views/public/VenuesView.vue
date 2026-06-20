<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AppNav from '@/components/layout/AppNav.vue'
import { venuesApi } from '@/api/client'
import type { Venue } from '@/types'

const venues = ref<Venue[]>([])
const loading = ref(true)

function accent(name: string) {
  const lower = name.toLowerCase()
  if (lower.includes('blue')) return '#3da9f5'
  if (lower.includes('orange')) return '#ff6400'
  if (lower.includes('green')) return '#2ec98a'
  if (lower.includes('yellow')) return '#f5a623'
  return '#3da9f5'
}

onMounted(async () => {
  try {
    venues.value = await venuesApi.list()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <AppNav />
    <section style="padding: var(--space-12) 0;">
      <div class="page-shell">
        <h1 class="section-title">Venues</h1>
        <p class="section-subtitle">Explore the Pyramid’s event spaces, capacities, amenities, and pricing.</p>

        <div v-if="loading" class="empty-state">
          <div class="spinner" />
        </div>

        <div v-else class="split-grid two-col">
          <article
            v-for="venue in venues"
            :key="venue.id"
            class="card"
            style="overflow: hidden;"
          >
            <div :style="{ height: '8px', background: accent(venue.name) }" />
            <div style="padding: var(--space-6); display: grid; gap: var(--space-4);">
              <div style="display: flex; justify-content: space-between; gap: var(--space-3);">
                <div>
                  <h2 style="margin: 0 0 0.35rem; font-size: 1.35rem;">{{ venue.name }}</h2>
                  <div style="color: var(--text-secondary);">
                    Floor {{ venue.floor }} · {{ venue.capacity_min }}–{{ venue.capacity_max }} guests
                  </div>
                </div>
                <span class="badge badge-info">{{ venue.status }}</span>
              </div>

              <p style="margin: 0; color: var(--text-secondary);">
                {{ venue.description || 'Flexible Pyramid venue with integrated operations support.' }}
              </p>

              <div style="display: grid; gap: var(--space-2);">
                <div style="font-size: 0.85rem; color: var(--text-tertiary);">Amenities</div>
                <div style="display: flex; flex-wrap: wrap; gap: var(--space-2);">
                  <span
                    v-for="item in venue.amenities"
                    :key="item"
                    class="badge badge-neutral"
                    style="text-transform: none;"
                  >
                    {{ item }}
                  </span>
                </div>
              </div>

              <div style="display: flex; justify-content: space-between; align-items: center; gap: var(--space-3);">
                <div>
                  <div style="font-size: 0.82rem; color: var(--text-tertiary);">Base hourly rate</div>
                  <strong>EUR {{ venue.base_price_per_hour }}</strong>
                </div>
                <RouterLink :to="`/book?venue_id=${venue.id}`" class="button button-primary">
                  Book this space
                </RouterLink>
              </div>
            </div>
          </article>
        </div>
      </div>
    </section>
  </div>
</template>
