<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const fullName = ref('')
const email = ref('')
const password = ref('')
const organization = ref('')
const phone = ref('')
const successMessage = ref('')

async function handleRegister() {
  try {
    const result = await auth.register({
      full_name: fullName.value,
      email: email.value,
      password: password.value,
      organization: organization.value || null,
      phone: phone.value || null,
    })

    if (result.requires_email_verification || !result.access_token) {
      successMessage.value =
        result.message ||
        'Account created. Check your email and use the confirmation link to finish signing in.'
      return
    }

    router.push('/account')
  } catch {
    // store exposes error
  }
}

async function handleGoogleRegister() {
  try {
    await auth.loginWithGoogle('/')
  } catch {
    // store exposes error
  }
}
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
    <section class="card" style="width: min(520px, 100%); padding: var(--space-8);">
      <RouterLink to="/" style="display: inline-flex; align-items: center; gap: var(--space-3); font-weight: 700; margin-bottom: var(--space-6);">
        <span style="color: var(--accent); font-size: 1.4rem;">⬡</span>
        <span>SpaceFlow</span>
      </RouterLink>

      <template v-if="successMessage">
        <h1 style="margin: 0 0 var(--space-3);">Check your email</h1>
        <p style="margin: 0 0 var(--space-6); color: var(--text-secondary);">
          {{ successMessage }}
        </p>
        <div style="display: flex; gap: var(--space-3); flex-wrap: wrap;">
          <RouterLink to="/login" class="button button-primary">Go to login</RouterLink>
          <RouterLink to="/" class="button button-secondary">Back home</RouterLink>
        </div>
      </template>

      <template v-else>
        <h1 style="margin: 0 0 var(--space-3);">Create your account</h1>
        <p style="margin: 0 0 var(--space-6); color: var(--text-secondary);">
          Register to submit event requests and follow their AI-driven review and approval process.
        </p>

        <form style="display: grid; gap: var(--space-4);" @submit.prevent="handleRegister">
          <div class="split-grid two-col">
            <label class="field">
              <span class="field-label">Full name</span>
              <input v-model="fullName" class="input" />
            </label>

            <label class="field">
              <span class="field-label">Email</span>
              <input v-model="email" class="input" type="email" />
            </label>
          </div>

          <div class="split-grid two-col">
            <label class="field">
              <span class="field-label">Organization</span>
              <input v-model="organization" class="input" />
            </label>

            <label class="field">
              <span class="field-label">Phone</span>
              <input v-model="phone" class="input" />
            </label>
          </div>

          <label class="field">
            <span class="field-label">Password</span>
            <input v-model="password" class="input" type="password" />
            <span class="field-hint">Minimum 8 characters.</span>
          </label>

          <div v-if="auth.error" class="card" style="padding: var(--space-3); color: var(--error); border-color: var(--error); background: var(--error-light);">
            {{ auth.error }}
          </div>

          <button type="submit" class="button button-primary" :disabled="auth.loading">
            {{ auth.loading ? 'Creating account...' : 'Create account' }}
          </button>

          <button type="button" class="button button-secondary" :disabled="auth.loading" @click="handleGoogleRegister">
            Continue with Google
          </button>
        </form>
      </template>
    </section>
  </main>
</template>
