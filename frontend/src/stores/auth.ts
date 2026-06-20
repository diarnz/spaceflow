import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { authApi, friendlyError } from '@/api/client'
import { requireSupabase, supabase, supabaseConfigured } from '@/lib/supabase'
import type { AuthResponse, User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('spaceflow_token'))
  const user = ref<User | null>(
    JSON.parse(localStorage.getItem('spaceflow_user') ?? 'null'),
  )
  const loading = ref(false)
  const initializing = ref(false)
  const error = ref<string | null>(null)
  let authListenerBound = false

  const isAuthenticated = computed(() => Boolean(token.value))
  const isStaff = computed(
    () => user.value?.role === 'admin' || user.value?.role === 'staff',
  )

  function clearLocalSession() {
    token.value = null
    user.value = null
    localStorage.removeItem('spaceflow_token')
    localStorage.removeItem('spaceflow_user')
  }

  function persistSession(data: AuthResponse) {
    if (!data.access_token || !data.user) {
      throw new Error(data.message || 'Authentication completed without an application session.')
    }
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('spaceflow_token', data.access_token)
    localStorage.setItem('spaceflow_user', JSON.stringify(data.user))
  }

  async function exchangeSupabaseToken(accessToken: string) {
    const data = await authApi.exchange({ access_token: accessToken })
    persistSession(data)
    return data
  }

  function bindSupabaseListener() {
    if (!supabase || authListenerBound) return
    supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_OUT') {
        clearLocalSession()
      }
    })
    authListenerBound = true
  }

  async function initialize() {
    if (initializing.value) return
    initializing.value = true
    error.value = null

    try {
      bindSupabaseListener()
      if (!token.value && supabaseConfigured) {
        const client = requireSupabase()
        const { data, error: sessionError } = await client.auth.getSession()
        if (sessionError) {
          throw sessionError
        }
        const accessToken = data.session?.access_token
        if (accessToken) {
          await exchangeSupabaseToken(accessToken)
        }
      }
    } catch (err) {
      clearLocalSession()
      error.value = friendlyError(err, 'Unable to restore your session.')
    } finally {
      initializing.value = false
    }
  }

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.login({ email, password })
      persistSession(data)

      if (supabaseConfigured) {
        const client = requireSupabase()
        void client.auth.signInWithPassword({ email, password }).catch(() => null)
      }

      return data
    } catch (err) {
      error.value = friendlyError(err, 'Unable to sign in.')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(payload: {
    email: string
    password: string
    full_name: string
    phone?: string | null
    organization?: string | null
  }) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.register(payload)

      if (data.access_token && data.user) {
        persistSession(data)
        if (supabaseConfigured) {
          const client = requireSupabase()
          void client.auth.signInWithPassword({
            email: payload.email,
            password: payload.password,
          }).catch(() => null)
        }
      } else {
        clearLocalSession()
      }
      return data
    } catch (err) {
      error.value = friendlyError(err, 'Unable to create account.')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loginWithGoogle(redirectPath = '/') {
    loading.value = true
    error.value = null
    try {
      const client = requireSupabase()
      const redirectTo = new URL('/auth/callback', window.location.origin)
      if (redirectPath.startsWith('/')) {
        redirectTo.searchParams.set('redirect', redirectPath)
      }

      const { error: oauthError } = await client.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: redirectTo.toString(),
        },
      })
      if (oauthError) {
        throw oauthError
      }
    } catch (err) {
      loading.value = false
      error.value = friendlyError(err, 'Unable to start Google sign-in.')
      throw err
    }
  }

  async function completeSupabaseCallback(code?: string | null) {
    loading.value = true
    error.value = null
    try {
      const client = requireSupabase()

      if (code) {
        const { error: exchangeError } = await client.auth.exchangeCodeForSession(code)
        if (exchangeError) {
          throw exchangeError
        }
      }

      const { data, error: sessionError } = await client.auth.getSession()
      if (sessionError) {
        throw sessionError
      }
      const accessToken = data.session?.access_token
      if (!accessToken) {
        throw new Error('No Supabase session was returned by the callback.')
      }

      return await exchangeSupabaseToken(accessToken)
    } catch (err) {
      error.value = friendlyError(err, 'Unable to complete sign-in.')
      throw err
    } finally {
      loading.value = false
    }
  }

  function logout() {
    clearLocalSession()
    if (supabaseConfigured) {
      const client = requireSupabase()
      void client.auth.signOut().catch(() => null)
    }
  }

  async function refreshUser() {
    const profile = await authApi.me()
    user.value = profile
    localStorage.setItem('spaceflow_user', JSON.stringify(profile))
    return profile
  }

  async function updateProfile(payload: {
    full_name?: string
    phone?: string | null
    organization?: string | null
  }) {
    loading.value = true
    error.value = null
    try {
      const profile = await authApi.updateProfile(payload)
      user.value = profile
      localStorage.setItem('spaceflow_user', JSON.stringify(profile))
      return profile
    } catch (err) {
      error.value = friendlyError(err, 'Unable to update profile.')
      throw err
    } finally {
      loading.value = false
    }
  }

  const displayName = computed(() => user.value?.full_name || user.value?.email || 'Guest')
  const initials = computed(() => {
    const name = displayName.value.trim()
    const parts = name.split(/\s+/).filter(Boolean)
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    return name.slice(0, 2).toUpperCase()
  })

  return {
    token,
    user,
    loading,
    initializing,
    error,
    isAuthenticated,
    isStaff,
    displayName,
    initials,
    initialize,
    login,
    register,
    loginWithGoogle,
    completeSupabaseCallback,
    refreshUser,
    updateProfile,
    logout,
  }
})
