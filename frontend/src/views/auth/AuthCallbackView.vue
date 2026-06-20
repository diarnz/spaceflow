<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const errorMessage = ref('')

const redirectTarget = computed(() =>
  typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
    ? route.query.redirect
    : null,
)

onMounted(async () => {
  try {
    const code = typeof route.query.code === 'string' ? route.query.code : null
    await auth.completeSupabaseCallback(code)

    const target =
      redirectTarget.value ??
      (auth.isStaff ? '/admin/dashboard' : '/')

    router.replace(target)
  } catch {
    errorMessage.value =
      auth.error || 'We could not finish your sign-in. Please try again.'
  }
})
</script>

<template>
  <main
    style="
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(180deg, var(--hero-gradient-start), var(--hero-gradient-end));
      padding: var(--space-6);
    "
  >
    <section class="card" style="width: min(460px, 100%); padding: var(--space-8); text-align: center;">
      <template v-if="!errorMessage">
        <h1 style="margin: 0 0 var(--space-3);">Completing sign in</h1>
        <p style="margin: 0; color: var(--text-secondary);">
          Finalizing your SpaceFlow session...
        </p>
      </template>

      <template v-else>
        <h1 style="margin: 0 0 var(--space-3);">Sign-in failed</h1>
        <p style="margin: 0 0 var(--space-6); color: var(--text-secondary);">
          {{ errorMessage }}
        </p>
        <div style="display: flex; justify-content: center; gap: var(--space-3); flex-wrap: wrap;">
          <RouterLink to="/login" class="button button-primary">Back to login</RouterLink>
          <RouterLink to="/register" class="button button-secondary">Create account</RouterLink>
        </div>
      </template>
    </section>
  </main>
</template>
