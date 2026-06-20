<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AppNav from '@/components/layout/AppNav.vue'
import RequestCard from '@/components/requests/RequestCard.vue'
import { requestsApi, venuesApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { EventRequestSummary, Venue } from '@/types'

const auth = useAuthStore()
const venues = ref<Venue[]>([])
const recentRequests = ref<EventRequestSummary[]>([])
const exploreUrl = import.meta.env.VITE_THREE_D_URL ?? 'http://localhost:3000'

const heroTitle = computed(() =>
  auth.isAuthenticated
    ? `Welcome back, ${auth.displayName.split(' ')[0]}.`
    : 'Book, design, and operate events with AI.',
)

const heroSubtitle = computed(() =>
  auth.isAuthenticated
    ? auth.isStaff
      ? 'Jump into operations, review requests, and manage Pyramid spaces from the admin dashboard.'
      : 'Submit new event requests, track review progress, and manage your profile from your account.'
    : 'SpaceFlow turns the Pyramid\'s spaces, inventory, quotations, AI room design, and operational planning into one live platform.',
)

function venueAccent(name: string) {
  const lower = name.toLowerCase()
  if (lower.includes('blue')) return '#3da9f5'
  if (lower.includes('orange')) return '#ff6400'
  if (lower.includes('green')) return '#2ec98a'
  if (lower.includes('yellow')) return '#f5a623'
  return '#3da9f5'
}

onMounted(async () => {
  venues.value = await venuesApi.list().catch(() => [])

  if (auth.isAuthenticated && !auth.isStaff) {
    const data = await requestsApi.list({ limit: 3 }).catch(() => null)
    recentRequests.value = data?.items ?? []
  }
})
</script>

<template>
  <div>
    <AppNav />

    <section
      style="
        background: linear-gradient(180deg, var(--hero-gradient-start), var(--hero-gradient-end));
        padding: var(--space-16) 0;
      "
    >
      <div class="page-shell" style="display: grid; grid-template-columns: 1.15fr 0.85fr; gap: var(--space-10); align-items: center;">
        <div>
          <span class="badge badge-info">Pyramid of Tirana operations platform</span>
          <h1 style="font-size: 3.4rem; line-height: 1.05; margin: var(--space-4) 0;">
            {{ heroTitle }}
          </h1>
          <p style="font-size: 1.1rem; color: var(--text-secondary); max-width: 640px; margin: 0 0 var(--space-6);">
            {{ heroSubtitle }}
          </p>
          <div style="display: flex; gap: var(--space-3); flex-wrap: wrap;">
            <RouterLink to="/book" class="button button-primary">
              {{ auth.isAuthenticated ? 'New request' : 'Submit Request' }}
            </RouterLink>
            <RouterLink
              v-if="auth.isAuthenticated && !auth.isStaff"
              to="/my-requests"
              class="button button-secondary"
            >
              My requests
            </RouterLink>
            <RouterLink
              v-else-if="auth.isAuthenticated && auth.isStaff"
              to="/admin/dashboard"
              class="button button-secondary"
            >
              Admin dashboard
            </RouterLink>
            <RouterLink v-else to="/venues" class="button button-secondary">
              Browse Venues
            </RouterLink>
            <RouterLink
              v-if="auth.isAuthenticated"
              to="/account"
              class="button button-secondary"
            >
              My profile
            </RouterLink>
            <RouterLink v-else to="/register" class="button button-secondary">
              Create account
            </RouterLink>
          </div>
        </div>

        <div class="card" style="padding: var(--space-6); display: grid; gap: var(--space-4);">
          <div v-if="auth.isAuthenticated" style="display: grid; gap: var(--space-3);">
            <div style="display: flex; align-items: center; gap: var(--space-3);">
              <div
                style="
                  width: 48px;
                  height: 48px;
                  border-radius: var(--radius-full);
                  background: var(--accent-light);
                  color: var(--accent-dark);
                  display: grid;
                  place-items: center;
                  font-weight: 700;
                "
              >
                {{ auth.initials }}
              </div>
              <div>
                <strong>{{ auth.displayName }}</strong>
                <div style="color: var(--text-secondary); font-size: 0.92rem;">{{ auth.user?.email }}</div>
              </div>
            </div>
            <div style="display: grid; gap: var(--space-2); color: var(--text-secondary); font-size: 0.92rem;">
              <div v-if="auth.user?.organization"><strong>Organization:</strong> {{ auth.user.organization }}</div>
              <div v-if="auth.user?.phone"><strong>Phone:</strong> {{ auth.user.phone }}</div>
              <div><strong>Role:</strong> {{ auth.isStaff ? 'Staff' : 'Client' }}</div>
            </div>
          </div>

          <div v-else style="display: flex; justify-content: space-between; gap: var(--space-3);">
            <div>
              <div style="font-size: 2rem; font-weight: 700;">5</div>
              <div style="color: var(--text-secondary);">Distinct spaces</div>
            </div>
            <div>
              <div style="font-size: 2rem; font-weight: 700;">AI</div>
              <div style="color: var(--text-secondary);">Proposal + 3D layout</div>
            </div>
            <div>
              <div style="font-size: 2rem; font-weight: 700;">Live</div>
              <div style="color: var(--text-secondary);">Inventory + requests</div>
            </div>
          </div>

          <div style="height: 220px; border-radius: var(--radius-lg); background: radial-gradient(circle at top right, rgba(61,169,245,0.22), transparent 42%), linear-gradient(135deg, #ffffff, #ecf7ff); display: flex; align-items: center; justify-content: center; font-size: 6rem;">
            🏛
          </div>
        </div>
      </div>
    </section>

    <section v-if="auth.isAuthenticated && !auth.isStaff && recentRequests.length" style="padding: var(--space-10) 0 0;">
      <div class="page-shell">
        <div style="display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); margin-bottom: var(--space-4);">
          <h2 class="section-title" style="margin: 0;">Your recent requests</h2>
          <RouterLink to="/my-requests" style="color: var(--accent); font-weight: 600;">View all</RouterLink>
        </div>
        <div class="split-grid three-col">
          <RequestCard
            v-for="request in recentRequests"
            :key="request.id"
            :request="request"
            :detail-path="`/my-requests/${request.id}`"
            :show-client="false"
          />
        </div>
      </div>
    </section>

    <section style="padding: var(--space-12) 0;">
      <div class="page-shell">
        <h2 class="section-title">Our spaces</h2>
        <p class="section-subtitle">Flexible rooms across the Pyramid, each with live availability and 3D visualization support.</p>

        <div class="split-grid four-col">
          <article
            v-for="venue in venues"
            :key="venue.id"
            class="card"
            style="overflow: hidden;"
          >
            <div :style="{ height: '6px', background: venueAccent(venue.name) }" />
            <div style="padding: var(--space-5); display: grid; gap: var(--space-3);">
              <div>
                <h3 style="margin: 0 0 0.35rem;">{{ venue.name }}</h3>
                <p style="margin: 0; color: var(--text-secondary);">
                  Floor {{ venue.floor }} · {{ venue.capacity_min }}–{{ venue.capacity_max }} guests
                </p>
              </div>
              <p style="margin: 0; color: var(--text-tertiary); min-height: 48px;">
                {{ venue.description || 'Multi-use Pyramid event space.' }}
              </p>
              <RouterLink
                :to="`/book?venue_id=${venue.id}`"
                class="button button-secondary"
              >
                Check availability
              </RouterLink>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section style="padding: var(--space-12) 0; background: var(--bg-secondary);">
      <div class="page-shell">
        <div
          class="card"
          style="
            padding: var(--space-8);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: var(--space-6);
            flex-wrap: wrap;
          "
        >
          <div style="max-width: 520px;">
            <h2 class="section-title" style="margin: 0 0 var(--space-3);">Explore</h2>
            <p style="margin: 0; color: var(--text-secondary);">
              Walk through the Pyramid in 3D — rooms, corridors, and layouts in an interactive viewer.
            </p>
          </div>
          <a
            :href="exploreUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="button button-primary"
          >
            Open 3D viewer
          </a>
        </div>
      </div>
    </section>
  </div>
</template>
