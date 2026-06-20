<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const email = ref('')
const password = ref('')

const redirectTarget = computed(() => {
  if (typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')) {
    return route.query.redirect
  }
  return ''
})

async function afterLogin() {
  if (redirectTarget.value) {
    router.push(redirectTarget.value)
    return
  }
  router.push(auth.isStaff ? '/admin/dashboard' : '/account')
}

async function handleLogin() {
  try {
    await auth.login(email.value, password.value)
    await afterLogin()
  } catch {
    // store already captures display error
  }
}

async function handleGoogleLogin() {
  try {
    const target = redirectTarget.value || (auth.isStaff ? '/admin/dashboard' : '/account')
    await auth.loginWithGoogle(target)
  } catch {
    // store already captures display error
  }
}

function fillDemo(role: 'admin' | 'client') {
  if (role === 'admin') {
    email.value = 'admin@spaceflo.dev'
    password.value = 'Admin1234!'
    return
  }
  email.value = ''
  password.value = ''
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
    <section class="card" style="width: min(480px, 100%); padding: var(--space-8);">
      <RouterLink to="/" style="display: inline-flex; align-items: center; gap: var(--space-3); font-weight: 700; margin-bottom: var(--space-6);">
        <span style="color: var(--accent); font-size: 1.4rem;">⬡</span>
        <span>SpaceFlow</span>
      </RouterLink>

      <h1 style="margin: 0 0 var(--space-3);">Welcome back</h1>
      <p style="margin: 0 0 var(--space-6); color: var(--text-secondary);">
        Sign in to submit requests, track progress, and manage your profile.
      </p>

      <form style="display: grid; gap: var(--space-4);" @submit.prevent="handleLogin">
        <label class="field">
          <span class="field-label">Email</span>
          <input v-model="email" class="input" type="email" autocomplete="email" />
        </label>

        <label class="field">
          <span class="field-label">Password</span>
          <input v-model="password" class="input" type="password" autocomplete="current-password" />
        </label>

        <div v-if="auth.error" class="card" style="padding: var(--space-3); color: var(--error); border-color: var(--error); background: var(--error-light);">
          {{ auth.error }}
        </div>

        <button type="submit" class="button button-primary" :disabled="auth.loading">
          {{ auth.loading ? 'Signing in...' : 'Sign in' }}
        </button>

        <button type="button" class="button button-secondary" :disabled="auth.loading" @click="handleGoogleLogin">
          Continue with Google
        </button>
      </form>

      <div class="card" style="margin-top: var(--space-5); padding: var(--space-4); background: var(--bg-secondary);">
        <strong style="display: block; margin-bottom: var(--space-2);">Demo accounts</strong>
        <p style="margin: 0 0 var(--space-3); color: var(--text-secondary); font-size: 0.92rem;">
          Staff demo for admin dashboard access. Clients should register or use Google sign-in.
        </p>
        <button type="button" class="button button-secondary" @click="fillDemo('admin')">
          Use staff demo login
        </button>
      </div>

      <div style="margin-top: var(--space-5); display: flex; justify-content: space-between; align-items: center; gap: var(--space-3);">
        <span style="color: var(--text-secondary); font-size: 0.9rem;">
          Need a client account?
        </span>
        <RouterLink to="/register" class="button button-secondary">
          Register
        </RouterLink>
      </div>
    </section>
  </main>
</template>
