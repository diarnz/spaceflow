<script setup lang="ts">
import { computed } from 'vue'

import type { EventStatus } from '@/types'

const props = defineProps<{
  status: EventStatus
}>()

const badgeClass = computed(() => {
  if (['approved', 'confirmed', 'completed'].includes(props.status)) return 'badge-success'
  if (['rejected', 'cancelled'].includes(props.status)) return 'badge-error'
  if (['under_review', 'quotation_sent'].includes(props.status)) return 'badge-warning'
  return 'badge-info'
})
</script>

<template>
  <span class="badge" :class="badgeClass">
    {{ status.replace('_', ' ') }}
  </span>
</template>
