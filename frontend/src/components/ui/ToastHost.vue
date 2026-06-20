<script setup lang="ts">
import { useNotificationsStore } from '@/stores/notifications'

const notifications = useNotificationsStore()
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack">
      <div
        v-for="item in notifications.items"
        :key="item.id"
        class="toast-item"
        :class="`toast-${item.variant}`"
      >
        <span>{{ item.title }}</span>
        <button
          type="button"
          class="button button-ghost"
          style="padding: 0.2rem 0.5rem; color: inherit;"
          @click="notifications.dismiss(item.id)"
        >
          ×
        </button>
      </div>
    </div>
  </Teleport>
</template>
