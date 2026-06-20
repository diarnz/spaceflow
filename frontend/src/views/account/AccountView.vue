<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AppNav from '@/components/layout/AppNav.vue'
import RequestCard from '@/components/requests/RequestCard.vue'
import { friendlyError, requestsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { EventRequestSummary } from '@/types'

const auth = useAuthStore()

const saving = ref(false)
const profileMessage = ref('')
const recentRequests = ref<EventRequestSummary[]>([])
const loadingRequests = ref(true)

const form = ref({
  full_name: '',
  phone: '',
  organization: '',
})

const roleLabel = computed(() => {
  if (auth.user?.role === 'admin') return 'Administrator'
  if (auth.user?.role === 'staff') return 'Operations staff'
  return 'Client account'
})

onMounted(async () => {
  if (auth.user) {
    form.value = {
      full_name: auth.user.full_name,
      phone: auth.user.phone ?? '',
      organization: auth.user.organization ?? '',
    }
  }

  if (auth.isAuthenticated && !auth.isStaff) {
    try {
      const data = await requestsApi.list({ limit: 3 })
      recentRequests.value = data.items
    } catch {
      recentRequests.value = []
    }
  }
  loadingRequests.value = false
})

async function saveProfile() {
  saving.value = true
  profileMessage.value = ''
  try {
    await auth.updateProfile({
      full_name: form.value.full_name.trim(),
      phone: form.value.phone.trim() || null,
      organization: form.value.organization.trim() || null,
    })
    profileMessage.value = 'Profile updated.'
  } catch (err) {
    profileMessage.value = friendlyError(err, 'Unable to save profile.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <AppNav />

    <section style="padding: var(--space-10) 0 var(--space-12);">
      <div class="page-shell" style="display: grid; gap: var(--space-8);">
        <div style="display: flex; justify-content: space-between; align-items: start; gap: var(--space-4); flex-wrap: wrap;">
          <div style="display: flex; align-items: center; gap: var(--space-4);">
            <div
              style="
                width: 64px;
                height: 64px;
                border-radius: var(--radius-full);
                background: var(--accent-light);
                color: var(--accent-dark);
                display: grid;
                place-items: center;
                font-weight: 700;
                font-size: 1.2rem;
              "
            >
              {{ auth.initials }}
            </div>
            <div>
              <h1 style="margin: 0 0 0.35rem;">{{ auth.displayName }}</h1>
              <p style="margin: 0; color: var(--text-secondary);">{{ auth.user?.email }}</p>
              <span class="badge badge-info" style="margin-top: var(--space-2); display: inline-block;">
                {{ roleLabel }}
              </span>
            </div>
          </div>

          <div style="display: flex; gap: var(--space-3); flex-wrap: wrap;">
            <RouterLink v-if="auth.isStaff" to="/admin/dashboard" class="button button-primary">
              Admin dashboard
            </RouterLink>
            <RouterLink v-else to="/my-requests" class="button button-primary">
              My requests
            </RouterLink>
            <RouterLink to="/book" class="button button-secondary">
              Book a space
            </RouterLink>
          </div>
        </div>

        <div class="split-grid two-col">
          <section class="card" style="padding: var(--space-6);">
            <h2 style="margin: 0 0 var(--space-5);">Profile</h2>
            <form style="display: grid; gap: var(--space-4);" @submit.prevent="saveProfile">
              <label class="field">
                <span class="field-label">Full name</span>
                <input v-model="form.full_name" class="input" required />
              </label>

              <label class="field">
                <span class="field-label">Email</span>
                <input :value="auth.user?.email" class="input" disabled />
                <span class="field-hint">Email is managed by your sign-in provider.</span>
              </label>

              <label class="field">
                <span class="field-label">Phone</span>
                <input v-model="form.phone" class="input" />
              </label>

              <label class="field">
                <span class="field-label">Organization</span>
                <input v-model="form.organization" class="input" />
              </label>

              <div v-if="profileMessage" class="card" style="padding: var(--space-3); background: var(--bg-secondary);">
                {{ profileMessage }}
              </div>

              <button type="submit" class="button button-primary" :disabled="saving">
                {{ saving ? 'Saving...' : 'Save profile' }}
              </button>
            </form>
          </section>

          <section class="card" style="padding: var(--space-6);">
            <h2 style="margin: 0 0 var(--space-4);">Your SpaceFlow access</h2>
            <ul style="margin: 0; padding-left: 1.1rem; color: var(--text-secondary); display: grid; gap: var(--space-3);">
              <li v-if="auth.isStaff">Review and approve incoming event requests.</li>
              <li v-if="auth.isStaff">Manage inventory, quotations, tasks, and 3D layouts.</li>
              <li v-if="!auth.isStaff">Submit and track event requests for Pyramid spaces.</li>
              <li v-if="!auth.isStaff">Receive AI venue recommendations and conflict checks.</li>
              <li>Sign in with email/password or Google (when enabled in Supabase).</li>
            </ul>

            <div style="margin-top: var(--space-6); display: grid; gap: var(--space-3);">
              <RouterLink to="/venues" class="button button-secondary">Browse venues</RouterLink>
              <button type="button" class="button button-secondary" @click="auth.logout(); $router.push('/login')">
                Sign out
              </button>
            </div>
          </section>
        </div>

        <section v-if="!auth.isStaff">
          <div style="display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); margin-bottom: var(--space-4);">
            <h2 style="margin: 0;">Recent requests</h2>
            <RouterLink to="/my-requests" style="color: var(--accent); font-weight: 600;">
              View all
            </RouterLink>
          </div>

          <div v-if="loadingRequests" style="color: var(--text-secondary);">Loading requests...</div>
          <div v-else-if="!recentRequests.length" class="card" style="padding: var(--space-6); text-align: center;">
            <p style="margin: 0 0 var(--space-4); color: var(--text-secondary);">
              You have not submitted any event requests yet.
            </p>
            <RouterLink to="/book" class="button button-primary">Submit your first request</RouterLink>
          </div>
          <div v-else class="split-grid three-col">
            <RequestCard
              v-for="request in recentRequests"
              :key="request.id"
              :request="request"
              :detail-path="`/my-requests/${request.id}`"
              :show-client="false"
            />
          </div>
        </section>
      </div>
    </section>
  </div>
</template>
