<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'

import AdminSidebar from './AdminSidebar.vue'
import AiChatPanel from '@/components/ai/AiChatPanel.vue'
import { useAiStore } from '@/stores/ai'
import { useWebsocketStore } from '@/stores/websocket'

const route = useRoute()
const ai = useAiStore()
const websocket = useWebsocketStore()

const pageTitle = computed(() => {
  if (route.path.startsWith('/admin/requests/') && route.params.id) {
    return 'Request Detail'
  }
  const titles: Record<string, string> = {
    '/admin/dashboard': 'Dashboard',
    '/admin/requests': 'Event Requests',
    '/admin/inventory': 'Inventory',
    '/admin/calendar': 'Calendar',
    '/admin/quotations': 'Quotations',
    '/admin/tasks': 'Operational Tasks',
    '/admin/visualization': '3D Visualization',
  }
  return titles[route.path] ?? 'Admin'
})

onMounted(() => {
  ;(window as any).__openAiPanel = () => {
    ai.setPanelState(true, ai.agentType, ai.context)
  }
})
</script>

<template>
  <div class="admin-shell">
    <AdminSidebar />

    <div class="admin-content-shell">
      <header class="admin-topbar">
        <div>
          <div style="font-size: 1.15rem; font-weight: 700;">{{ pageTitle }}</div>
          <div style="color: var(--text-tertiary); font-size: 0.85rem;">
            Pyramid of Tirana operations console
          </div>
        </div>

        <div style="display: inline-flex; align-items: center; gap: var(--space-3);">
          <div
            class="badge"
            :class="websocket.connected ? 'badge-success' : 'badge-warning'"
          >
            <span
              style="
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: currentColor;
                display: inline-block;
              "
            />
            {{ websocket.connected ? 'Live' : 'Reconnecting' }}
          </div>

          <button
            type="button"
            class="button button-primary"
            @click="ai.setPanelState(true, ai.agentType, ai.context)"
          >
            ✦ AI Copilot
          </button>
        </div>
      </header>

      <main class="admin-main">
        <RouterView />
      </main>
    </div>

    <AiChatPanel />
  </div>
</template>
