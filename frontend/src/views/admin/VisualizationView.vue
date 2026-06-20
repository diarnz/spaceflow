<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import ThreeDFrame from '@/components/visualization/ThreeDFrame.vue'
import { venuesApi } from '@/api/client'
import { useAiStore } from '@/stores/ai'
import type { Venue } from '@/types'

const ai = useAiStore()
const venues = ref<Venue[]>([])
const selectedVenueId = ref<string>('')
const externalThreeDUrl = import.meta.env.VITE_THREE_D_URL ?? 'http://localhost:3000'

const selectedVenue = computed(
  () => venues.value.find((venue) => venue.id === selectedVenueId.value) ?? null,
)

function openDesigner() {
  ai.resetConversation()
  ai.setPanelState(true, 'room_designer', {
    venue_name: selectedVenue.value?.name ?? '',
  })
}

onMounted(async () => {
  venues.value = await venuesApi.list().catch(() => [])
  selectedVenueId.value = venues.value[0]?.id ?? ''
})
</script>

<template>
  <section style="display: grid; gap: var(--space-4);">
    <div class="card" style="padding: var(--space-4); display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap;">
      <div style="display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap;">
        <label class="field" style="min-width: 220px;">
          <span class="field-label">Venue</span>
          <select v-model="selectedVenueId" class="select">
            <option v-for="venue in venues" :key="venue.id" :value="venue.id">
              {{ venue.name }}
            </option>
          </select>
        </label>
        <div style="color: var(--text-secondary);">
          {{ selectedVenue?.three_d_room_id || 'No 3D room linked' }}
        </div>
      </div>

      <div style="display: flex; gap: var(--space-3);">
        <button type="button" class="button button-primary" @click="openDesigner">
          Design with AI
        </button>
        <a
          class="button button-secondary"
          :href="externalThreeDUrl"
          target="_blank"
          rel="noreferrer"
        >
          Open fullscreen
        </a>
      </div>
    </div>

    <ThreeDFrame :room-id="selectedVenue?.three_d_room_id" />
  </section>
</template>
