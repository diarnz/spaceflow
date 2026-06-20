<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterView } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useWebsocketStore } from '@/stores/websocket'
import ToastHost from '@/components/ui/ToastHost.vue'

const auth = useAuthStore()
const websocket = useWebsocketStore()

onMounted(() => {
  if (auth.isStaff) {
    websocket.connect()
  }
})

watch(
  () => auth.isStaff,
  (isStaff) => {
    if (isStaff) {
      websocket.connect()
    } else {
      websocket.disconnect()
    }
  },
)
</script>

<template>
  <RouterView />
  <ToastHost />
</template>
