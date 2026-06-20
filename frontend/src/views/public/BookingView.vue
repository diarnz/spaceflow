<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppNav from '@/components/layout/AppNav.vue'
import { friendlyError, requestsApi, venuesApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import type { EventType, Venue } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const notifications = useNotificationsStore()

const step = ref(0)
const submitting = ref(false)
const venues = ref<Venue[]>([])
const success = ref(false)

const today = new Date().toISOString().slice(0, 10)

const form = ref({
  title: '',
  event_type: 'conference' as EventType,
  description: '',
  requested_date: '',
  start_time: '',
  end_time: '',
  attendee_count: 50,
  venue_id: String(route.query.venue_id ?? ''),
  special_requirements: '',
  setup_time_minutes: 60,
  teardown_time_minutes: 60,
})

const selectedVenue = computed(() =>
  venues.value.find((venue) => venue.id === form.value.venue_id) ?? null,
)

const eventDuration = computed(() => {
  if (!form.value.start_time || !form.value.end_time) return null
  const [sh, sm] = form.value.start_time.split(':').map(Number)
  const [eh, em] = form.value.end_time.split(':').map(Number)
  if ([sh, sm, eh, em].some((value) => Number.isNaN(value))) return null
  const startMinutes = sh * 60 + sm
  const endMinutes = eh * 60 + em
  return endMinutes - startMinutes
})

const stepErrors = computed<string[]>(() => {
  const errors: string[] = []

  if (step.value === 0) {
    if (!form.value.title.trim()) {
      errors.push('Add an event title.')
    } else if (form.value.title.trim().length < 3) {
      errors.push('Event title must be at least 3 characters.')
    }
    if (!form.value.requested_date) {
      errors.push('Choose an event date.')
    } else if (form.value.requested_date < today) {
      errors.push('Event date cannot be in the past.')
    }
    if (!form.value.start_time) {
      errors.push('Choose a start time.')
    }
    if (!form.value.end_time) {
      errors.push('Choose an end time.')
    }
    if (
      form.value.start_time &&
      form.value.end_time &&
      eventDuration.value !== null &&
      eventDuration.value <= 0
    ) {
      errors.push('End time must be after start time on the same day.')
    }
    if (eventDuration.value !== null && eventDuration.value > 0 && eventDuration.value < 30) {
      errors.push('Events must be at least 30 minutes long.')
    }
    if (eventDuration.value !== null && eventDuration.value > 16 * 60) {
      errors.push('Events longer than 16 hours need to be split across multiple days.')
    }
    if (!form.value.attendee_count || form.value.attendee_count < 1) {
      errors.push('Provide an attendee count of at least 1.')
    } else if (form.value.attendee_count > 10000) {
      errors.push('Attendee count cannot exceed 10,000.')
    }
  }

  if (step.value === 1) {
    if (!form.value.venue_id) {
      errors.push('Select a venue.')
    } else if (selectedVenue.value && form.value.attendee_count > selectedVenue.value.capacity_max) {
      errors.push(
        `${selectedVenue.value.name} fits up to ${selectedVenue.value.capacity_max} guests; reduce attendees or pick a larger space.`,
      )
    } else if (
      selectedVenue.value &&
      selectedVenue.value.status !== 'active'
    ) {
      errors.push(`${selectedVenue.value.name} is currently ${selectedVenue.value.status} and cannot accept events.`)
    }
  }

  return errors
})

const canContinue = computed(() => stepErrors.value.length === 0)

onMounted(async () => {
  const savedDraft = localStorage.getItem('spaceflow_booking_draft')
  if (savedDraft) {
    try {
      form.value = {
        ...form.value,
        ...JSON.parse(savedDraft),
      }
    } catch {
      // ignore bad local draft
    }
  }
  try {
    venues.value = await venuesApi.list()
  } catch (err) {
    notifications.push(friendlyError(err, 'Could not load venues.'), 'error')
  }
})

watch(
  form,
  (value) => {
    localStorage.setItem('spaceflow_booking_draft', JSON.stringify(value))
  },
  { deep: true },
)

async function submitRequest() {
  if (stepErrors.value.length) {
    notifications.push(stepErrors.value[0], 'warning')
    return
  }

  if (!auth.isAuthenticated) {
    notifications.push('Please sign in before submitting your request.', 'warning')
    router.push('/login?redirect=/book')
    return
  }

  submitting.value = true
  try {
    await requestsApi.create({
      ...form.value,
      title: form.value.title.trim(),
      description: form.value.description.trim() || undefined,
      special_requirements: form.value.special_requirements.trim() || undefined,
      start_time: `${form.value.start_time}:00`,
      end_time: `${form.value.end_time}:00`,
    })
    localStorage.removeItem('spaceflow_booking_draft')
    success.value = true
    notifications.push('Request submitted. AI is now analyzing it.', 'success')
  } catch (err) {
    notifications.push(friendlyError(err, 'Unable to submit request.'), 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <AppNav />
    <section style="padding: var(--space-12) 0;">
      <div class="page-shell" style="max-width: 880px;">
        <div v-if="success" class="card" style="padding: var(--space-12); text-align: center;">
          <div
            style="
              width: 72px;
              height: 72px;
              border-radius: 50%;
              background: var(--success-light);
              color: var(--success);
              display: inline-flex;
              align-items: center;
              justify-content: center;
              font-size: 2rem;
              margin-bottom: var(--space-4);
            "
          >
            ✓
          </div>
          <h1 style="margin: 0 0 var(--space-3);">Request submitted</h1>
          <p style="margin: 0 0 var(--space-6); color: var(--text-secondary);">
            Your event request is now in the system. The AI intake agent will analyze venue fit, asset availability, quotation, and conflicts automatically.
          </p>
          <div style="display: flex; justify-content: center; gap: var(--space-3);">
            <button type="button" class="button button-secondary" @click="router.push('/')">
              Back to home
            </button>
            <button type="button" class="button button-primary" @click="router.push('/login')">
              Sign in to track status
            </button>
          </div>
        </div>

        <template v-else>
          <h1 class="section-title">Book a space</h1>
          <p class="section-subtitle">
            Submit your event request and let SpaceFlow’s AI generate the best operational proposal.
          </p>

          <div style="display: flex; gap: var(--space-3); margin-bottom: var(--space-6);">
            <span class="badge" :class="step === 0 ? 'badge-info' : 'badge-neutral'">1. Event</span>
            <span class="badge" :class="step === 1 ? 'badge-info' : 'badge-neutral'">2. Space</span>
            <span class="badge" :class="step === 2 ? 'badge-info' : 'badge-neutral'">3. Review</span>
          </div>

          <div class="card" style="padding: var(--space-6); display: grid; gap: var(--space-6);">
            <div v-if="step === 0" class="split-grid two-col">
              <label class="field">
                <span class="field-label">Event title</span>
                <input v-model="form.title" class="input" placeholder="AlbTech Annual Summit 2026" />
              </label>

              <label class="field">
                <span class="field-label">Event type</span>
                <select v-model="form.event_type" class="select">
                  <option value="conference">Conference</option>
                  <option value="workshop">Workshop</option>
                  <option value="concert">Concert</option>
                  <option value="exhibition">Exhibition</option>
                  <option value="hackathon">Hackathon</option>
                  <option value="dinner">Dinner</option>
                  <option value="private">Private</option>
                  <option value="other">Other</option>
                </select>
              </label>

              <label class="field">
                <span class="field-label">Event date</span>
                <input
                  v-model="form.requested_date"
                  class="input"
                  type="date"
                  :min="today"
                />
              </label>

              <label class="field">
                <span class="field-label">Attendees</span>
                <input
                  v-model.number="form.attendee_count"
                  class="input"
                  type="number"
                  min="1"
                  max="10000"
                />
              </label>

              <label class="field">
                <span class="field-label">Start time</span>
                <input v-model="form.start_time" class="input" type="time" />
              </label>

              <label class="field">
                <span class="field-label">End time</span>
                <input v-model="form.end_time" class="input" type="time" />
                <span v-if="eventDuration !== null && eventDuration > 0" class="field-hint">
                  Duration: {{ Math.floor(eventDuration / 60) }}h {{ eventDuration % 60 }}m
                </span>
              </label>

              <label class="field" style="grid-column: 1 / -1;">
                <span class="field-label">Description</span>
                <textarea v-model="form.description" class="textarea" rows="4" placeholder="Describe the event and goals." />
              </label>
            </div>

            <div v-else-if="step === 1" style="display: grid; gap: var(--space-4);">
              <div class="split-grid two-col">
                <button
                  v-for="venue in venues"
                  :key="venue.id"
                  type="button"
                  class="card"
                  :style="{
                    padding: '1rem',
                    textAlign: 'left',
                    cursor: 'pointer',
                    borderColor: form.venue_id === venue.id ? 'var(--accent)' : 'var(--border)',
                    boxShadow: form.venue_id === venue.id ? '0 0 0 3px var(--accent-light)' : 'var(--shadow-sm)',
                    opacity: venue.status === 'active' ? 1 : 0.65,
                  }"
                  :disabled="venue.status !== 'active'"
                  @click="form.venue_id = venue.id"
                >
                  <div style="display: flex; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-2);">
                    <strong>{{ venue.name }}</strong>
                    <span
                      class="badge"
                      :class="venue.status === 'active' ? 'badge-info' : 'badge-warning'"
                    >
                      {{ venue.status }}
                    </span>
                  </div>
                  <div style="color: var(--text-secondary);">
                    Floor {{ venue.floor }} · {{ venue.capacity_min }}–{{ venue.capacity_max }} people
                  </div>
                  <div
                    v-if="form.attendee_count > venue.capacity_max"
                    style="color: var(--error); margin-top: var(--space-2); font-size: 0.85rem;"
                  >
                    Capacity: max {{ venue.capacity_max }} guests (you have {{ form.attendee_count }}).
                  </div>
                  <div style="color: var(--text-tertiary); margin-top: var(--space-2);">
                    {{ venue.description || 'Flexible Pyramid event space.' }}
                  </div>
                </button>
              </div>

              <label class="field">
                <span class="field-label">Special requirements</span>
                <textarea
                  v-model="form.special_requirements"
                  class="textarea"
                  rows="4"
                  placeholder="Need microphones, projectors, whiteboards, stage, catering tables..."
                />
              </label>
            </div>

            <div v-else style="display: grid; gap: var(--space-4);">
              <div class="card" style="padding: var(--space-5); background: var(--bg-secondary);">
                <div class="split-grid two-col">
                  <div>
                    <div style="color: var(--text-tertiary); font-size: 0.82rem;">Title</div>
                    <strong>{{ form.title }}</strong>
                  </div>
                  <div>
                    <div style="color: var(--text-tertiary); font-size: 0.82rem;">Type</div>
                    <strong>{{ form.event_type }}</strong>
                  </div>
                  <div>
                    <div style="color: var(--text-tertiary); font-size: 0.82rem;">Date</div>
                    <strong>{{ form.requested_date }}</strong>
                  </div>
                  <div>
                    <div style="color: var(--text-tertiary); font-size: 0.82rem;">Time</div>
                    <strong>{{ form.start_time }} – {{ form.end_time }}</strong>
                  </div>
                  <div>
                    <div style="color: var(--text-tertiary); font-size: 0.82rem;">Attendees</div>
                    <strong>{{ form.attendee_count }}</strong>
                  </div>
                  <div>
                    <div style="color: var(--text-tertiary); font-size: 0.82rem;">Venue</div>
                    <strong>{{ selectedVenue?.name || 'Not selected' }}</strong>
                  </div>
                </div>
              </div>
              <p style="margin: 0; color: var(--text-secondary);">
                Once submitted, the request will trigger AI intake automatically: venue matching, asset checks, quotation estimate, and conflict detection.
              </p>
            </div>

            <div
              v-if="stepErrors.length && step < 2"
              class="card"
              style="
                padding: var(--space-3) var(--space-4);
                background: var(--warning-light);
                border-color: var(--warning);
                color: var(--text-primary);
                display: grid;
                gap: 0.25rem;
              "
            >
              <span
                v-for="message in stepErrors"
                :key="message"
                style="font-size: 0.9rem;"
              >
                {{ message }}
              </span>
            </div>

            <div style="display: flex; justify-content: space-between; gap: var(--space-3);">
              <button
                type="button"
                class="button button-secondary"
                :disabled="step === 0"
                @click="step = Math.max(0, step - 1)"
              >
                Back
              </button>

              <div style="display: flex; gap: var(--space-3);">
                <button
                  v-if="step < 2"
                  type="button"
                  class="button button-primary"
                  :disabled="!canContinue"
                  @click="step = Math.min(2, step + 1)"
                >
                  Continue
                </button>
                <button
                  v-else
                  type="button"
                  class="button button-primary"
                  :disabled="submitting"
                  @click="submitRequest"
                >
                  {{ submitting ? 'Submitting...' : 'Submit request' }}
                </button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>
