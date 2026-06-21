import axios, { AxiosError, type AxiosInstance } from 'axios'

import type {
  AIAgentResponse,
  AIChatResponse,
  AIConversationDetail,
  AIConversationSummary,
  AIToolInfo,
  AuthResponse,
  Asset,
  AssetAvailabilityResponse,
  AssetSummaryItem,
  BookingPreviewResponse,
  BulkReserveResponse,
  EventRequestCreatePayload,
  EventRequestDetail,
  EventRequestSummary,
  PaginatedResponse,
  QuotationResponse,
  ReservationResponse,
  RoomLayoutResponse,
  StatusTransitionResponse,
  TaskResponse,
  TaskItem,
  User,
  Venue,
  VenueAvailabilityResponse,
} from '@/types'

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api/v1'

export const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('spaceflow_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('spaceflow_token')
      localStorage.removeItem('spaceflow_user')
      const path = window.location.pathname
      if (path !== '/login' && path !== '/register') {
        window.location.href = `/login?redirect=${encodeURIComponent(path)}`
      }
    }
    return Promise.reject(error)
  },
)

const FRIENDLY_FIELDS: Record<string, string> = {
  title: 'Event title',
  event_type: 'Event type',
  description: 'Description',
  requested_date: 'Event date',
  start_time: 'Start time',
  end_time: 'End time',
  attendee_count: 'Attendee count',
  venue_id: 'Venue',
  setup_time_minutes: 'Setup duration',
  teardown_time_minutes: 'Teardown duration',
  email: 'Email',
  password: 'Password',
  full_name: 'Full name',
  phone: 'Phone',
  organization: 'Organization',
}

function humanizeFieldPath(loc: unknown[] | undefined): string {
  if (!loc || loc.length === 0) return ''
  const parts = loc.filter((part) => part !== 'body' && part !== 'query' && part !== 'path')
  if (!parts.length) return ''
  const key = String(parts[parts.length - 1])
  return FRIENDLY_FIELDS[key] ?? key.replace(/_/g, ' ')
}

function humanizeMessage(msg: string, field: string): string {
  const lowered = msg.toLowerCase()
  if (lowered.includes('end_time must be after start_time')) {
    return 'End time must be later than start time on the same day.'
  }
  if (lowered.includes('field required')) {
    return `${field || 'This field'} is required.`
  }
  if (lowered.includes('value is not a valid email')) {
    return 'Please enter a valid email address.'
  }
  if (lowered.includes('string should have at least')) {
    const match = msg.match(/at least (\d+) character/)
    return match
      ? `${field || 'This field'} must be at least ${match[1]} characters.`
      : `${field || 'This field'} is too short.`
  }
  if (lowered.includes('input should be greater than')) {
    return `${field || 'This value'} must be greater than ${msg.split('than ').pop() ?? ''}.`
  }
  // Strip "Value error, " prefix that pydantic adds
  const cleaned = msg.replace(/^value error,\s*/i, '').replace(/^value error:\s*/i, '')
  if (field) return `${field}: ${cleaned}`
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
}

/**
 * Convert any axios/backend error into a single readable user-facing string.
 * Handles FastAPI 422 detail arrays, plain detail strings, network failures,
 * and unknown errors. Never returns raw JSON.
 */
export function friendlyError(err: unknown, fallback = 'Something went wrong.'): string {
  if (!err) return fallback

  if (err instanceof AxiosError || (err as any)?.isAxiosError) {
    const axiosErr = err as AxiosError<any>

    if (axiosErr.code === 'ERR_NETWORK' || axiosErr.message === 'Network Error') {
      return 'Cannot reach the server. Please check your connection and try again.'
    }
    if (axiosErr.code === 'ECONNABORTED') {
      return 'The request took too long. Please try again.'
    }

    const status = axiosErr.response?.status
    const data = axiosErr.response?.data

    if (data && typeof data === 'object') {
      const detail = (data as any).detail

      if (Array.isArray(detail)) {
        const lines = detail.map((entry: any) => {
          const field = humanizeFieldPath(entry?.loc)
          const msg = String(entry?.msg ?? '')
          return humanizeMessage(msg, field)
        })
        return lines.join(' ')
      }

      if (typeof detail === 'string' && detail.trim()) {
        return detail
      }

      if (typeof (data as any).message === 'string') {
        return (data as any).message
      }
    }

    if (status === 401) return 'Your session expired. Please sign in again.'
    if (status === 403) return 'You do not have permission to perform this action.'
    if (status === 404) return 'The requested item was not found.'
    if (status === 409) return 'There is a scheduling or data conflict. Please review and try again.'
    if (status === 429) return 'Too many requests. Please slow down and retry.'
    if (status && status >= 500) return 'The server is temporarily unavailable. Please try again shortly.'

    if (axiosErr.message) return axiosErr.message
  }

  if (err instanceof Error && err.message) return err.message
  if (typeof err === 'string') return err

  return fallback
}

export const authApi = {
  register: (payload: {
    email: string
    password: string
    full_name: string
    phone?: string | null
    organization?: string | null
  }) => http.post<AuthResponse>('/auth/register', payload).then((r) => r.data),

  login: (payload: { email: string; password: string }) =>
    http.post<AuthResponse>('/auth/login', payload).then((r) => r.data),

  exchange: (payload: { access_token: string }) =>
    http.post<AuthResponse>('/auth/exchange', payload).then((r) => r.data),

  me: () => http.get<User>('/auth/me').then((r) => r.data),

  updateProfile: (payload: {
    full_name?: string
    phone?: string | null
    organization?: string | null
  }) => http.patch<User>('/auth/me', payload).then((r) => r.data),
}

export const venuesApi = {
  list: (activeOnly = true) =>
    http
      .get<Venue[]>('/venues', { params: { active_only: activeOnly } })
      .then((r) => r.data),

  get: (venueId: string) =>
    http.get<Venue>(`/venues/${venueId}`).then((r) => r.data),

  availability: (venueId: string, date: string, durationHours: number) =>
    http
      .get<VenueAvailabilityResponse>(`/venues/${venueId}/availability`, {
        params: { date, duration_hours: durationHours },
      })
      .then((r) => r.data),
}

export const requestsApi = {
  list: (params?: {
    status?: string
    venue_id?: string
    limit?: number
    offset?: number
  }) =>
    http
      .get<PaginatedResponse<EventRequestSummary>>('/requests', { params })
      .then((r) => r.data),

  get: (requestId: string) =>
    http.get<EventRequestDetail>(`/requests/${requestId}`).then((r) => r.data),

  create: (payload: EventRequestCreatePayload) =>
    http.post<EventRequestDetail>('/requests', payload).then((r) => r.data),

  update: (requestId: string, payload: Partial<EventRequestCreatePayload>) =>
    http.put<EventRequestDetail>(`/requests/${requestId}`, payload).then((r) => r.data),

  assignVenue: (requestId: string, venueId: string) =>
    http
      .post<StatusTransitionResponse>(`/requests/${requestId}/assign-venue`, {
        venue_id: venueId,
      })
      .then((r) => r.data),

  approve: (requestId: string) =>
    http
      .post<StatusTransitionResponse>(`/requests/${requestId}/approve`)
      .then((r) => r.data),

  reject: (requestId: string, reason: string) =>
    http
      .post<StatusTransitionResponse>(`/requests/${requestId}/reject`, { reason })
      .then((r) => r.data),

  complete: (requestId: string) =>
    http
      .post<StatusTransitionResponse>(`/requests/${requestId}/complete`)
      .then((r) => r.data),

  conflicts: (requestId: string) =>
    http.get<{
      request_id: string
      has_blocking_conflicts: boolean
      has_warnings: boolean
      conflicts: EventRequestDetail['ai_proposal_json'] extends { conflicts: infer T } ? T : any[]
    }>(`/requests/${requestId}/conflicts`).then((r) => r.data),
}

export const assetsApi = {
  list: (category?: string) =>
    http
      .get<Asset[]>('/assets', { params: { category } })
      .then((r) => r.data),

  summary: () => http.get<AssetSummaryItem[]>('/assets/summary').then((r) => r.data),

  get: (assetId: string) =>
    http.get<Asset>(`/assets/${assetId}`).then((r) => r.data),

  availability: (assetId: string, start: string, end: string) =>
    http
      .get<AssetAvailabilityResponse>(`/assets/${assetId}/availability`, {
        params: { start, end },
      })
      .then((r) => r.data),
}

export const reservationsApi = {
  list: (requestId: string) =>
    http
      .get<ReservationResponse[]>('/reservations', { params: { request_id: requestId } })
      .then((r) => r.data),

  bulkReserve: (
    requestId: string,
    assets: { asset_id: string; quantity: number }[],
  ) =>
    http
      .post<BulkReserveResponse>(`/reservations/bulk/${requestId}`, { assets })
      .then((r) => r.data),
}

export const quotationsApi = {
  generate: (requestId: string) =>
    http
      .post<QuotationResponse>(`/quotations/generate/${requestId}`)
      .then((r) => r.data),

  get: (quotationId: string) =>
    http.get<QuotationResponse>(`/quotations/${quotationId}`).then((r) => r.data),

  update: (
    quotationId: string,
    payload: {
      line_items?: QuotationResponse['line_items']
      admin_notes?: string | null
      tax_rate?: string | number
    },
  ) =>
    http.put<QuotationResponse>(`/quotations/${quotationId}`, payload).then((r) => r.data),

  send: (quotationId: string) =>
    http.post<QuotationResponse>(`/quotations/${quotationId}/send`).then((r) => r.data),
}

export const tasksApi = {
  list: (params?: {
    request_id?: string
    assigned_to?: string
    status?: string
  }) =>
    http.get<TaskResponse[]>('/tasks', { params }).then((r) => r.data),

  generate: (requestId: string) =>
    http.post<TaskResponse[]>(`/tasks/generate/${requestId}`).then((r) => r.data),

  myTasks: () => http.get<TaskResponse[]>('/tasks/my-tasks').then((r) => r.data),

  workers: () => http.get<User[]>('/tasks/workers').then((r) => r.data),

  update: (
    taskId: string,
    payload: {
      title?: string
      description?: string | null
      pickup_room?: string | null
      destination_room?: string | null
      items?: TaskItem[]
      instructions?: string | null
      assigned_to?: string | null
      due_at?: string
      status?: string
      priority?: number
    },
  ) => http.put<TaskResponse>(`/tasks/${taskId}`, payload).then((r) => r.data),

  complete: (taskId: string) =>
    http.post<TaskResponse>(`/tasks/${taskId}/complete`).then((r) => r.data),
}

export const layoutsApi = {
  list: (venueId: string) =>
    http
      .get<RoomLayoutResponse[]>('/layouts', { params: { venue_id: venueId } })
      .then((r) => r.data),

  current: (threeDRoomId: string) =>
    http
      .get<RoomLayoutResponse | null>('/layouts/current', {
        params: { three_d_room_id: threeDRoomId },
      })
      .then((r) => r.data),

  byRequest: (requestId: string) =>
    http
      .get<RoomLayoutResponse | null>(`/layouts/by-request/${requestId}`)
      .then((r) => r.data),
}

export const bookingsApi = {
  preview: (payload: {
    three_d_room_id?: string
    venue_id?: string
    requested_date: string
    start_time: string
    end_time: string
    event_type?: string
    setup_time_minutes?: number
    teardown_time_minutes?: number
    items: unknown[]
  }) => http.post<BookingPreviewResponse>('/bookings/preview', payload).then((r) => r.data),
}

export const aiApi = {
  chat: (payload: {
    message: string
    agent_type: string
    context?: Record<string, unknown>
    conversation_id?: string | null
  }) => http.post<AIChatResponse>('/ai/chat', payload).then((r) => r.data),

  run: (payload: {
    message: string
    agent_type: string
    context?: Record<string, unknown>
    conversation_id?: string | null
  }) => http.post<AIAgentResponse>('/ai/run', payload).then((r) => r.data),

  designRoom: (payload: {
    venue_name: string
    prompt: string
    event_request_id?: string | null
    event_date_start?: string | null
    event_date_end?: string | null
  }) => http.post('/ai/design-room', payload).then((r) => r.data),

  detectConflicts: (requestId: string) =>
    http.post('/ai/detect-conflicts', { request_id: requestId }).then((r) => r.data),

  generateTasks: (requestId: string) =>
    http.post(`/ai/generate-tasks/${requestId}`).then((r) => r.data),

  intake: (requestId: string) =>
    http.post(`/ai/intake/${requestId}`).then((r) => r.data),

  conversations: () =>
    http
      .get<PaginatedResponse<AIConversationSummary>>('/ai/conversations')
      .then((r) => r.data),

  conversation: (conversationId: string) =>
    http
      .get<AIConversationDetail>(`/ai/conversations/${conversationId}`)
      .then((r) => r.data),

  deleteConversation: (conversationId: string) =>
    http.delete(`/ai/conversations/${conversationId}`).then((r) => r.data),

  tools: () => http.get<AIToolInfo[]>('/ai/tools').then((r) => r.data),
}
