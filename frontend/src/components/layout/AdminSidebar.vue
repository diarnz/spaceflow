<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useWebsocketStore } from '@/stores/websocket'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const websocket = useWebsocketStore()

const navItems = computed(() => [
  { to: '/admin/dashboard', label: 'Dashboard', icon: '◉' },
  { to: '/admin/requests', label: 'Requests', icon: '📋' },
  { to: '/admin/inventory', label: 'Inventory', icon: '📦' },
  { to: '/admin/calendar', label: 'Calendar', icon: '📅' },
  { to: '/admin/quotations', label: 'Quotations', icon: '€' },
  { to: '/admin/tasks', label: 'Tasks', icon: '✓' },
  { to: '/admin/visualization', label: '3D View', icon: '🏛' },
])

function handleLogout() {
  websocket.disconnect()
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <aside
    style="
      background: var(--surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      position: sticky;
      top: 0;
    "
  >
    <div
      style="
        min-height: var(--topbar-height);
        display: flex;
        align-items: center;
        gap: var(--space-3);
        padding: 0 var(--space-5);
        border-bottom: 1px solid var(--border);
        font-weight: 700;
        font-size: 1.05rem;
      "
    >
      <span style="color: var(--accent); font-size: 1.35rem;">⬡</span>
      <span>SpaceFlow</span>
    </div>

    <nav style="display: flex; flex-direction: column; gap: var(--space-1); padding: var(--space-4);">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        :style="{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          padding: '0.75rem 0.9rem',
          borderRadius: '0.75rem',
          fontWeight: '600',
          color: route.path === item.to || route.path.startsWith(item.to + '/') ? 'var(--accent-dark)' : 'var(--text-secondary)',
          background: route.path === item.to || route.path.startsWith(item.to + '/') ? 'var(--accent-light)' : 'transparent',
        }"
      >
        <span>{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div style="margin-top: auto; padding: var(--space-4); border-top: 1px solid var(--border);">
      <div style="display: flex; flex-direction: column; gap: 0.35rem; margin-bottom: var(--space-4);">
        <strong>{{ auth.user?.full_name }}</strong>
        <span style="color: var(--text-tertiary); font-size: 0.85rem; text-transform: capitalize;">
          {{ auth.user?.role }}
        </span>
      </div>
      <button type="button" class="button button-secondary" style="width: 100%;" @click="handleLogout">
        Sign Out
      </button>
    </div>
  </aside>
</template>
