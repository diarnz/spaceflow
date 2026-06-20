<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  roomId?: string | null
}>()

const threeDUrl = import.meta.env.VITE_THREE_D_URL ?? 'http://localhost:3000'

const frameUrl = computed(() => {
  if (!props.roomId) return threeDUrl
  const url = new URL(threeDUrl)
  url.searchParams.set('autoRoom', props.roomId)
  return url.toString()
})
</script>

<template>
  <div
    class="card"
    style="
      overflow: hidden;
      min-height: 620px;
      background: #0f1720;
    "
  >
    <iframe
      :src="frameUrl"
      title="Pyramid 3D View"
      style="display: block; width: 100%; height: 620px; border: 0;"
      allow="fullscreen"
    />
  </div>
</template>
