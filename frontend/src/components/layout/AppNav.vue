<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useWebsocketStore } from '@/stores/websocket'

const auth = useAuthStore()
const websocket = useWebsocketStore()
const router = useRouter()

const dashboardTarget = computed(() =>
  auth.isStaff ? '/admin/dashboard' : '/account',
)

function handleLogout() {
  websocket.disconnect()
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <header
    style="
      position: sticky;
      top: 0;
      z-index: 20;
      backdrop-filter: blur(12px);
      background: var(--nav-bg);
      border-bottom: 1px solid var(--nav-border);
    "
  >
    <div
      class="page-shell"
      style="display: flex; align-items: center; justify-content: space-between; min-height: 72px; gap: var(--space-4);"
    >
      <RouterLink
        to="/"
        style="display: inline-flex; align-items: center; gap: var(--space-3); font-weight: 700; font-size: 1.15rem;"
      >
        <span style="color: var(--accent); font-size: 1.4rem;">⬡</span>
        <span>SpaceFlow</span>
      </RouterLink>

      <nav style="display: inline-flex; align-items: center; gap: var(--space-3); flex-wrap: wrap;">
        <RouterLink to="/venues" style="color: var(--text-secondary); font-weight: 600;">
          Venues
        </RouterLink>
        <RouterLink to="/book" style="color: var(--text-secondary); font-weight: 600;">
          Book a Space
        </RouterLink>

        <template v-if="auth.isAuthenticated">
          <RouterLink
            v-if="!auth.isStaff"
            to="/my-requests"
            style="color: var(--text-secondary); font-weight: 600;"
          >
            My Requests
          </RouterLink>
          <RouterLink
            :to="dashboardTarget"
            style="color: var(--text-secondary); font-weight: 600;"
          >
            {{ auth.isStaff ? 'Admin' : 'Account' }}
          </RouterLink>

          <RouterLink
            to="/account"
            style="
              display: inline-flex;
              align-items: center;
              gap: var(--space-2);
              padding: 0.35rem 0.7rem 0.35rem 0.35rem;
              border-radius: var(--radius-full);
              background: var(--bg-secondary);
              border: 1px solid var(--border-light);
              font-weight: 600;
            "
          >
            <span
              style="
                width: 28px;
                height: 28px;
                border-radius: var(--radius-full);
                background: var(--accent-light);
                color: var(--accent-dark);
                display: grid;
                place-items: center;
                font-size: 0.75rem;
              "
            >
              {{ auth.initials }}
            </span>
            <span style="max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              {{ auth.displayName }}
            </span>
          </RouterLink>

          <button type="button" class="button button-secondary" @click="handleLogout">
            Sign Out
          </button>
        </template>

        <template v-else>
          <RouterLink to="/login" class="button button-secondary">Sign In</RouterLink>
          <RouterLink to="/register" class="button button-primary">Get Started</RouterLink>
        </template>
      </nav>
    </div>
  </header>
</template>
