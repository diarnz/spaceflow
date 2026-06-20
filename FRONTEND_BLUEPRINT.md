# SpaceFlow Frontend Blueprint
## Vue 3 + Vite + TypeScript — Port 5173
### JunctionX Tirana 2026 | Complete Implementation Reference

---

## Table of Contents

1. [Overview & Decisions](#1-overview--decisions)
2. [Phase F1 — Project Setup, Design System & Configuration](#phase-f1--project-setup-design-system--configuration)
3. [Phase F2 — Public Booking Portal](#phase-f2--public-booking-portal)
4. [Phase F3 — Authentication Flow](#phase-f3--authentication-flow)
5. [Phase F4 — Admin: Requests & Pipeline](#phase-f4--admin-requests--pipeline)
6. [Phase F5 — Admin: Inventory Management](#phase-f5--admin-inventory-management)
7. [Phase F6 — Admin: Calendar & Scheduling](#phase-f6--admin-calendar--scheduling)
8. [Phase F7 — Admin: Quotations](#phase-f7--admin-quotations)
9. [Phase F8 — Admin: Task Board](#phase-f8--admin-task-board)
10. [Phase F9 — 3D Visualization Tab](#phase-f9--3d-visualization-tab)
11. [Phase F10 — AI Copilot Chat Panel](#phase-f10--ai-copilot-chat-panel)
12. [Admin WebSocket Integration](#12-admin-websocket-integration)
13. [Vite Config, tsconfig & package.json](#13-vite-config-tsconfig--packagejson)

---

## 1. Overview & Decisions

### Location
`frontend/` inside `junctionxtirana/` root — sibling of `backend/` and `tumo_3d_model/`.

### Tech Stack
| Layer | Choice | Reason |
|-------|--------|--------|
| Framework | Vue 3 Composition API + `<script setup>` | Reactive, ergonomic, excellent TypeScript |
| Build | Vite | Instant HMR, first-class Vue support |
| Language | TypeScript strict | Type safety against backend schemas |
| Routing | Vue Router 4 | Nested routes, navigation guards |
| State | Pinia | Lightweight, modular, SSR-ready |
| HTTP | Axios | Interceptors for auth + error handling |
| Validation | VeeValidate + Yup | Form schema validation |
| Calendar | FullCalendar v6 Vue3 | Rich calendar with drag-drop |
| Charts | Chart.js + vue-chartjs | Dashboard widgets |
| UI Utilities | @vueuse/core | useWebSocket, useLocalStorage, etc. |
| CSS | Custom properties (SpaceFlow Design Tokens) | No Tailwind dependency; matches color pack |

### Ports
- Frontend: **http://localhost:5173** (Vite dev)
- Backend API: **http://localhost:8080/api/v1**
- Backend WS: **ws://localhost:8080/ws/admin**
- 3D App: **http://localhost:3000**

### Route Guard Strategy
Navigation guard in `router/index.ts` checks Pinia auth store:
- Routes with `meta.requiresAuth = true` → redirect to `/login` if no token
- Routes with `meta.requiresRole = ['admin','staff']` → redirect to `/` if wrong role
- `/login` and `/register` → redirect to `/admin/dashboard` if already authenticated

---

## Phase F1 — Project Setup, Design System & Configuration

### Directory Structure

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── package.json
├── .env
├── .env.example
└── src/
    ├── main.ts
    ├── App.vue
    ├── types/
    │   └── index.ts                    ← All TypeScript interfaces
    ├── api/
    │   ├── client.ts                   ← Axios instance + interceptors
    │   ├── auth.ts
    │   ├── venues.ts
    │   ├── requests.ts
    │   ├── assets.ts
    │   ├── tasks.ts
    │   ├── layouts.ts
    │   └── ai.ts
    ├── stores/
    │   ├── auth.ts
    │   ├── requests.ts
    │   ├── assets.ts
    │   ├── notifications.ts
    │   ├── websocket.ts
    │   └── ai.ts
    ├── router/
    │   └── index.ts
    ├── composables/
    │   ├── useAuth.ts
    │   ├── useRequests.ts
    │   ├── useAssets.ts
    │   ├── useToast.ts
    │   └── useAiChat.ts
    ├── components/
    │   ├── layout/
    │   │   ├── AppNav.vue
    │   │   ├── AdminSidebar.vue
    │   │   └── AdminLayout.vue
    │   ├── ui/
    │   │   ├── SpBadge.vue
    │   │   ├── SpButton.vue
    │   │   ├── SpCard.vue
    │   │   ├── SpInput.vue
    │   │   ├── SpSelect.vue
    │   │   ├── SpModal.vue
    │   │   ├── SpToast.vue
    │   │   └── SpSpinner.vue
    │   ├── requests/
    │   │   ├── RequestCard.vue
    │   │   ├── RequestStatusBadge.vue
    │   │   ├── ConflictAlert.vue
    │   │   └── AiProposalCard.vue
    │   ├── inventory/
    │   │   ├── AssetCard.vue
    │   │   └── AssetAvailabilityBar.vue
    │   ├── tasks/
    │   │   └── TaskCard.vue
    │   ├── ai/
    │   │   ├── AiChatPanel.vue
    │   │   ├── AiMessage.vue
    │   │   └── AiTypingIndicator.vue
    │   └── visualization/
    │       └── ThreeDFrame.vue
    ├── views/
    │   ├── public/
    │   │   ├── HomeView.vue
    │   │   ├── VenuesView.vue
    │   │   └── BookingView.vue
    │   ├── auth/
    │   │   ├── LoginView.vue
    │   │   └── RegisterView.vue
    │   └── admin/
    │       ├── DashboardView.vue
    │       ├── RequestsView.vue
    │       ├── RequestDetailView.vue
    │       ├── InventoryView.vue
    │       ├── CalendarView.vue
    │       ├── QuotationsView.vue
    │       ├── TasksView.vue
    │       └── VisualizationView.vue
    └── assets/
        └── styles/
            ├── tokens.css
            ├── base.css
            └── utilities.css
```

---

### `frontend/.env`

```env
VITE_API_BASE_URL=http://localhost:8080/api/v1
VITE_WS_URL=ws://localhost:8080
VITE_THREE_D_URL=http://localhost:3000
```

### `frontend/.env.example`

```env
VITE_API_BASE_URL=http://localhost:8080/api/v1
VITE_WS_URL=ws://localhost:8080
VITE_THREE_D_URL=http://localhost:3000
```

---

### `frontend/src/assets/styles/tokens.css`

```css
:root {
  /* ── Backgrounds ─────────────────────────────────── */
  --bg-primary:          #ffffff;
  --bg-secondary:        #f4f9fd;
  --bg-tertiary:         #e8f2fb;
  --surface:             #ffffff;
  --surface-hover:       #f0f7fc;

  /* ── Borders ─────────────────────────────────────── */
  --border:              #d4e5f2;
  --border-light:        #e6eff7;

  /* ── Navigation ─────────────────────────────────── */
  --nav-bg:              rgba(255, 255, 255, 0.90);
  --nav-border:          rgba(212, 229, 242, 0.6);

  /* ── Accent (Pyramid blue) ───────────────────────── */
  --accent:              #3da9f5;
  --accent-hover:        #2b96e0;
  --accent-light:        #e0f0fd;
  --accent-dark:         #1a7cc7;

  /* ── Text ────────────────────────────────────────── */
  --text-primary:        #12263a;
  --text-secondary:      #4a6a85;
  --text-tertiary:       #7a9bb5;
  --text-on-accent:      #ffffff;

  /* ── Status ──────────────────────────────────────── */
  --success:             #2ec98a;
  --success-light:       #e4f9f0;
  --warning:             #f5a623;
  --warning-light:       #fef4e0;
  --error:               #f04848;
  --error-light:         #fde8e8;
  --info:                #3da9f5;
  --info-light:          #e0f0fd;

  /* ── Venue Colors ────────────────────────────────── */
  --venue-blue:          #3da9f5;
  --venue-orange:        #ff6400;
  --venue-green:         #2ec98a;
  --venue-yellow:        #f5a623;
  --venue-corridor:      #9b59b6;

  /* ── Shadows ─────────────────────────────────────── */
  --shadow-sm:           0 1px 3px rgba(18, 38, 58, 0.06);
  --shadow-md:           0 4px 12px rgba(18, 38, 58, 0.09);
  --shadow-lg:           0 8px 32px rgba(18, 38, 58, 0.13);
  --overlay:             rgba(18, 38, 58, 0.40);

  /* ── Gradients ───────────────────────────────────── */
  --hero-gradient-start: #ffffff;
  --hero-gradient-end:   #cce8f8;
  --gradient-blue:       #95ccf0;
  --gradient-mid:        #cce8f8;

  /* ── Typography ──────────────────────────────────── */
  --font-sans:           'Inter', system-ui, -apple-system, sans-serif;
  --text-xs:             0.75rem;
  --text-sm:             0.875rem;
  --text-base:           1rem;
  --text-lg:             1.125rem;
  --text-xl:             1.25rem;
  --text-2xl:            1.5rem;
  --text-3xl:            1.875rem;
  --text-4xl:            2.25rem;

  /* ── Spacing ─────────────────────────────────────── */
  --space-1:  0.25rem;  --space-2:  0.5rem;   --space-3:  0.75rem;
  --space-4:  1rem;     --space-5:  1.25rem;  --space-6:  1.5rem;
  --space-8:  2rem;     --space-10: 2.5rem;   --space-12: 3rem;
  --space-16: 4rem;

  /* ── Border Radius ───────────────────────────────── */
  --radius-sm:   0.375rem;
  --radius-md:   0.5rem;
  --radius-lg:   0.75rem;
  --radius-xl:   1rem;
  --radius-2xl:  1.5rem;
  --radius-full: 9999px;

  /* ── Transitions ─────────────────────────────────── */
  --transition-fast: 120ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;

  /* ── Z-index layers ──────────────────────────────── */
  --z-dropdown: 100;
  --z-modal:    200;
  --z-toast:    300;
  --z-sidebar:  50;
  --z-nav:      60;
  --z-ai-panel: 150;

  /* ── Sidebar ─────────────────────────────────────── */
  --sidebar-width:       240px;
  --sidebar-collapsed:   64px;
  --topbar-height:       60px;
}
```

---

### `frontend/src/assets/styles/base.css`

```css
@import './tokens.css';
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { font-size: 16px; scroll-behavior: smooth; }

body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  color: var(--text-primary);
  background: var(--bg-primary);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--accent); text-decoration: none; transition: color var(--transition-fast); }
a:hover { color: var(--accent-hover); }

h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  line-height: 1.25;
  color: var(--text-primary);
}
h1 { font-size: var(--text-4xl); }
h2 { font-size: var(--text-3xl); }
h3 { font-size: var(--text-2xl); }
h4 { font-size: var(--text-xl); }

p { color: var(--text-secondary); line-height: 1.7; }

input, textarea, select {
  font-family: var(--font-sans);
  font-size: var(--text-base);
}

button { cursor: pointer; font-family: var(--font-sans); }

img { max-width: 100%; display: block; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: var(--radius-full); }
::-webkit-scrollbar-thumb:hover { background: var(--text-tertiary); }

.page-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}

.section { padding: var(--space-16) 0; }

.visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0);
  white-space: nowrap; border: 0;
}
```

---

### `frontend/src/assets/styles/utilities.css`

```css
/* Flex helpers */
.flex         { display: flex; }
.flex-col     { flex-direction: column; }
.items-center { align-items: center; }
.items-start  { align-items: flex-start; }
.justify-between { justify-content: space-between; }
.justify-center  { justify-content: center; }
.flex-1       { flex: 1; }
.gap-2        { gap: var(--space-2); }
.gap-3        { gap: var(--space-3); }
.gap-4        { gap: var(--space-4); }
.gap-6        { gap: var(--space-6); }

/* Grid helpers */
.grid         { display: grid; }
.grid-2       { grid-template-columns: repeat(2, 1fr); }
.grid-3       { grid-template-columns: repeat(3, 1fr); }
.grid-4       { grid-template-columns: repeat(4, 1fr); }

/* Spacing */
.mt-2  { margin-top: var(--space-2); }
.mt-4  { margin-top: var(--space-4); }
.mt-6  { margin-top: var(--space-6); }
.mt-8  { margin-top: var(--space-8); }
.mb-4  { margin-bottom: var(--space-4); }
.mb-6  { margin-bottom: var(--space-6); }
.p-4   { padding: var(--space-4); }
.p-6   { padding: var(--space-6); }

/* Text */
.text-sm      { font-size: var(--text-sm); }
.text-xs      { font-size: var(--text-xs); }
.text-lg      { font-size: var(--text-lg); }
.font-medium  { font-weight: 500; }
.font-semibold { font-weight: 600; }
.text-muted   { color: var(--text-secondary); }
.text-tertiary { color: var(--text-tertiary); }
.text-center  { text-align: center; }
.text-accent  { color: var(--accent); }
.text-success { color: var(--success); }
.text-error   { color: var(--error); }
.text-warning { color: var(--warning); }

/* Display */
.hidden       { display: none !important; }
.block        { display: block; }
.inline-flex  { display: inline-flex; }
.w-full       { width: 100%; }
.h-full       { height: 100%; }
.overflow-hidden { overflow: hidden; }
.truncate     { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rounded-full { border-radius: var(--radius-full); }
.cursor-pointer { cursor: pointer; }
```

---

### `frontend/src/types/index.ts`

```typescript
// ─── Auth ────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'staff' | 'client'
  phone: string | null
  organization: string | null
  is_active: boolean
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  role?: 'client'
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

// ─── Venues ──────────────────────────────────────────────────────────────────

export interface Venue {
  id: string
  name: string
  description: string | null
  capacity_min: number
  capacity_max: number
  base_price_per_hour: number
  three_d_room_id: string | null
  amenities: string[]
  is_active: boolean
}

export interface VenueAvailabilitySlot {
  start: string
  end: string
  duration_hours: number
}

export interface VenueAvailability {
  venue_id: string
  date: string
  is_fully_available: boolean
  available_slots: VenueAvailabilitySlot[]
}

// ─── Requests ────────────────────────────────────────────────────────────────

export type RequestStatus =
  | 'submitted'
  | 'under_review'
  | 'pending_info'
  | 'approved'
  | 'rejected'
  | 'completed'
  | 'cancelled'

export type EventType =
  | 'conference'
  | 'workshop'
  | 'concert'
  | 'exhibition'
  | 'hackathon'
  | 'dinner'
  | 'other'

export interface AiProposal {
  status?: string
  summary?: string
  recommended_venue?: {
    id: string | null
    name: string | null
    reason: string
  }
  availability?: {
    is_fully_available: boolean
    available_slots: VenueAvailabilitySlot[]
  }
  required_assets?: {
    name: string
    requested: number
    available: number
    can_fulfill: boolean
  }[]
  estimate?: {
    subtotal: number
    tax: number
    total: number
    breakdown: { category: string; name: string; total: number }[]
  }
  conflicts?: Conflict[]
  tool_calls?: { tool: string; args: object; result: object }[]
}

export interface EventRequestSummary {
  id: string
  title: string
  event_type: EventType
  status: RequestStatus
  requested_date: string
  start_time: string
  end_time: string
  attendee_count: number
  venue_id: string | null
  venue: Venue | null
  client_id: string
  client: User | null
  has_ai_proposal: boolean
  has_conflicts: boolean
  created_at: string
}

export interface EventRequestDetail extends EventRequestSummary {
  description: string | null
  setup_time_minutes: number
  teardown_time_minutes: number
  special_requirements: string | null
  assigned_staff_id: string | null
  rejection_reason: string | null
  ai_proposal_json: AiProposal | null
  updated_at: string
}

export interface EventRequestCreate {
  title: string
  event_type: EventType
  description?: string
  requested_date: string
  start_time: string
  end_time: string
  attendee_count: number
  setup_time_minutes?: number
  teardown_time_minutes?: number
  special_requirements?: string
  venue_id?: string
}

// ─── Conflicts ───────────────────────────────────────────────────────────────

export interface Conflict {
  severity: 'blocking' | 'warning'
  type: string
  description: string
  suggestion: string
  affected_resource?: string
}

// ─── Assets ──────────────────────────────────────────────────────────────────

export type AssetCategory =
  | 'seating'
  | 'tables'
  | 'av_equipment'
  | 'staging'
  | 'lighting'
  | 'misc'

export interface Asset {
  id: string
  name: string
  description: string | null
  category: AssetCategory
  tracking_type: 'pool' | 'individual'
  total_quantity: number
  unit_price: number
  three_d_item_key: string | null
  is_active: boolean
}

export interface AssetAvailability {
  asset_id: string
  name: string
  total_quantity: number
  reserved_quantity: number
  available_quantity: number
}

// ─── Tasks ───────────────────────────────────────────────────────────────────

export type TaskStatus = 'pending' | 'in_progress' | 'blocked' | 'done' | 'cancelled'
export type TaskType =
  | 'setup'
  | 'teardown'
  | 'av_config'
  | 'catering'
  | 'security'
  | 'cleaning'
  | 'coordination'
  | 'other'

export interface Task {
  id: string
  event_request_id: string
  title: string
  description: string | null
  task_type: TaskType
  assigned_to: string | null
  due_at: string
  completed_at: string | null
  status: TaskStatus
  priority: 1 | 2 | 3   // 1=high, 2=medium, 3=low
  ai_generated: boolean
  created_at: string
  updated_at: string
}

// ─── Quotations ──────────────────────────────────────────────────────────────

export type QuotationStatus = 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired'

export interface QuotationLineItem {
  id?: string
  description: string
  category: string
  quantity: number
  unit_price: number
  total: number
}

export interface Quotation {
  id: string
  event_request_id: string
  status: QuotationStatus
  line_items: QuotationLineItem[]
  subtotal: number
  discount_amount: number
  tax_rate: number
  tax_amount: number
  total: number
  valid_until: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

// ─── Room Layouts ────────────────────────────────────────────────────────────

export interface RoomLayout {
  id: string
  venue_id: string
  event_request_id: string | null
  name: string
  items_json: object[]
  source: 'manual' | 'ai_agent' | 'template'
  ai_prompt: string | null
  created_at: string
}

// ─── AI ──────────────────────────────────────────────────────────────────────

export interface AiMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  tool_calls?: { tool: string; args: object; result: object }[]
}

export interface AiChatRequest {
  message: string
  agent_type: 'copilot' | 'room_designer' | 'intake' | 'conflict_detector' | 'planner'
  context?: object
  conversation_id?: string | null
}

export interface AiChatResponse {
  response: string
  tool_calls_made: { tool: string; args: object; result: object }[]
  conversation_id: string
}

// ─── Pagination ──────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

// ─── WebSocket ───────────────────────────────────────────────────────────────

export interface WsMessage {
  type: string
  payload: Record<string, unknown>
}
```

---

### `frontend/src/api/client.ts`

```typescript
import axios, { type AxiosInstance } from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api/v1'

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// Attach JWT token from localStorage on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('spaceflow_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 globally — clear token and redirect to login
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('spaceflow_token')
      localStorage.removeItem('spaceflow_user')
      if (window.location.pathname.startsWith('/admin')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)
```

---

### `frontend/src/api/auth.ts`

```typescript
import { api } from './client'
import type { AuthResponse, LoginRequest, RegisterRequest, User } from '@/types'

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<AuthResponse>('/auth/login', data).then((r) => r.data),

  register: (data: RegisterRequest) =>
    api.post<AuthResponse>('/auth/register', data).then((r) => r.data),

  me: () => api.get<User>('/auth/me').then((r) => r.data),
}
```

---

### `frontend/src/api/venues.ts`

```typescript
import { api } from './client'
import type { Venue, VenueAvailability, PaginatedResponse } from '@/types'

export const venuesApi = {
  list: (activeOnly = true) =>
    api.get<PaginatedResponse<Venue>>('/venues', { params: { active_only: activeOnly } })
      .then((r) => r.data),

  get: (id: string) =>
    api.get<Venue>(`/venues/${id}`).then((r) => r.data),

  availability: (id: string, date: string, durationHours: number) =>
    api.get<VenueAvailability>(`/venues/${id}/availability`, {
      params: { date, duration_hours: durationHours },
    }).then((r) => r.data),
}
```

---

### `frontend/src/api/requests.ts`

```typescript
import { api } from './client'
import type {
  EventRequestCreate,
  EventRequestDetail,
  EventRequestSummary,
  PaginatedResponse,
  StatusTransitionResponse,
} from '@/types'

interface StatusTransitionResponse {
  id: string
  previous_status: string
  new_status: string
  message: string
}

export const requestsApi = {
  list: (params?: {
    status?: string
    venue_id?: string
    limit?: number
    offset?: number
  }) =>
    api.get<PaginatedResponse<EventRequestSummary>>('/requests', { params })
      .then((r) => r.data),

  get: (id: string) =>
    api.get<EventRequestDetail>(`/requests/${id}`).then((r) => r.data),

  create: (data: EventRequestCreate) =>
    api.post<EventRequestDetail>('/requests', data).then((r) => r.data),

  update: (id: string, data: Partial<EventRequestCreate>) =>
    api.put<EventRequestDetail>(`/requests/${id}`, data).then((r) => r.data),

  approve: (id: string) =>
    api.post<StatusTransitionResponse>(`/requests/${id}/approve`).then((r) => r.data),

  reject: (id: string, reason: string) =>
    api.post<StatusTransitionResponse>(`/requests/${id}/reject`, { reason })
      .then((r) => r.data),

  complete: (id: string) =>
    api.post<StatusTransitionResponse>(`/requests/${id}/complete`).then((r) => r.data),

  assignVenue: (id: string, venueId: string) =>
    api.post<StatusTransitionResponse>(`/requests/${id}/assign-venue`, { venue_id: venueId })
      .then((r) => r.data),

  conflicts: (id: string) =>
    api.get(`/requests/${id}/conflicts`).then((r) => r.data),
}
```

---

### `frontend/src/api/assets.ts`

```typescript
import { api } from './client'
import type { Asset, AssetAvailability, PaginatedResponse } from '@/types'

export const assetsApi = {
  list: (params?: { category?: string; active_only?: boolean }) =>
    api.get<PaginatedResponse<Asset>>('/assets', { params }).then((r) => r.data),

  get: (id: string) => api.get<Asset>(`/assets/${id}`).then((r) => r.data),

  availability: (id: string, start: string, end: string) =>
    api.get<AssetAvailability>(`/assets/${id}/availability`, {
      params: { start, end },
    }).then((r) => r.data),

  summary: () => api.get('/assets/summary').then((r) => r.data),
}
```

---

### `frontend/src/api/tasks.ts`

```typescript
import { api } from './client'
import type { Task, PaginatedResponse } from '@/types'

export const tasksApi = {
  list: (params?: { request_id?: string; status?: string }) =>
    api.get<PaginatedResponse<Task>>('/tasks', { params }).then((r) => r.data),

  update: (id: string, data: Partial<Task>) =>
    api.put<Task>(`/tasks/${id}`, data).then((r) => r.data),

  complete: (id: string) =>
    api.post<Task>(`/tasks/${id}/complete`).then((r) => r.data),

  myTasks: () =>
    api.get<Task[]>('/tasks/my-tasks').then((r) => r.data),

  overdue: () =>
    api.get<Task[]>('/tasks/overdue').then((r) => r.data),

  generate: (requestId: string) =>
    api.post(`/ai/generate-tasks/${requestId}`).then((r) => r.data),
}
```

---

### `frontend/src/api/ai.ts`

```typescript
import { api } from './client'
import type { AiChatRequest, AiChatResponse } from '@/types'

export const aiApi = {
  chat: (data: AiChatRequest) =>
    api.post<AiChatResponse>('/ai/chat', data).then((r) => r.data),

  designRoom: (data: {
    venue_name: string
    prompt: string
    event_request_id?: string
    event_date_start?: string
    event_date_end?: string
  }) => api.post('/ai/design-room', data).then((r) => r.data),

  detectConflicts: (requestId: string) =>
    api.post('/ai/detect-conflicts', { request_id: requestId }).then((r) => r.data),

  generateTasks: (requestId: string) =>
    api.post(`/ai/generate-tasks/${requestId}`).then((r) => r.data),

  triggerIntake: (requestId: string) =>
    api.post(`/ai/intake/${requestId}`).then((r) => r.data),

  listConversations: () =>
    api.get('/ai/conversations').then((r) => r.data),

  getConversation: (id: string) =>
    api.get(`/ai/conversations/${id}`).then((r) => r.data),

  deleteConversation: (id: string) =>
    api.delete(`/ai/conversations/${id}`),
}
```

---

### `frontend/src/api/layouts.ts`

```typescript
import { api } from './client'
import type { RoomLayout } from '@/types'

export const layoutsApi = {
  list: (venueId: string) =>
    api.get<RoomLayout[]>('/layouts', { params: { venue_id: venueId } })
      .then((r) => r.data),

  get: (id: string) =>
    api.get<RoomLayout>(`/layouts/${id}`).then((r) => r.data),
}
```

---

### `frontend/src/stores/auth.ts`

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User, LoginRequest, RegisterRequest } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('spaceflow_token'))
  const user = ref<User | null>(
    JSON.parse(localStorage.getItem('spaceflow_user') ?? 'null'),
  )
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isStaff = computed(
    () => user.value?.role === 'admin' || user.value?.role === 'staff',
  )

  function _persist(t: string, u: User) {
    token.value = t
    user.value = u
    localStorage.setItem('spaceflow_token', t)
    localStorage.setItem('spaceflow_user', JSON.stringify(u))
  }

  async function login(data: LoginRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await authApi.login(data)
      _persist(res.access_token, res.user)
      return res.user
    } catch (err: any) {
      error.value = err.response?.data?.detail ?? 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(data: RegisterRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await authApi.register(data)
      _persist(res.access_token, res.user)
      return res.user
    } catch (err: any) {
      error.value = err.response?.data?.detail ?? 'Registration failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('spaceflow_token')
    localStorage.removeItem('spaceflow_user')
  }

  return { token, user, loading, error, isAuthenticated, isAdmin, isStaff, login, register, logout }
})
```

---

### `frontend/src/stores/requests.ts`

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { requestsApi } from '@/api/requests'
import type { EventRequestDetail, EventRequestSummary } from '@/types'

export const useRequestsStore = defineStore('requests', () => {
  const items = ref<EventRequestSummary[]>([])
  const activeRequest = ref<EventRequestDetail | null>(null)
  const total = ref(0)
  const loading = ref(false)

  async function fetchList(params?: { status?: string; limit?: number; offset?: number }) {
    loading.value = true
    try {
      const res = await requestsApi.list(params)
      items.value = res.items
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id: string) {
    loading.value = true
    try {
      activeRequest.value = await requestsApi.get(id)
    } finally {
      loading.value = false
    }
  }

  function prependRequest(req: EventRequestSummary) {
    items.value.unshift(req)
    total.value += 1
  }

  return { items, activeRequest, total, loading, fetchList, fetchOne, prependRequest }
})
```

---

### `frontend/src/stores/assets.ts`

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { assetsApi } from '@/api/assets'
import type { Asset } from '@/types'

export const useAssetsStore = defineStore('assets', () => {
  const items = ref<Asset[]>([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      const res = await assetsApi.list()
      items.value = res.items
    } finally {
      loading.value = false
    }
  }

  return { items, loading, fetchAll }
})
```

---

### `frontend/src/stores/notifications.ts`

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastVariant = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  message: string
  variant: ToastVariant
  timeout: number
}

export const useNotificationsStore = defineStore('notifications', () => {
  const toasts = ref<Toast[]>([])

  function show(message: string, variant: ToastVariant = 'info', timeout = 4000) {
    const id = crypto.randomUUID()
    toasts.value.push({ id, message, variant, timeout })
    setTimeout(() => dismiss(id), timeout)
  }

  function dismiss(id: string) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  return { toasts, show, dismiss }
})
```

---

### `frontend/src/stores/websocket.ts`

```typescript
import { defineStore } from 'pinia'
import { ref, onUnmounted } from 'vue'
import { useNotificationsStore } from './notifications'
import { useRequestsStore } from './requests'
import type { WsMessage } from '@/types'

const WS_URL = `${import.meta.env.VITE_WS_URL ?? 'ws://localhost:8080'}/ws/admin`

export const useWebSocketStore = defineStore('websocket', () => {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let attempts = 0

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return
    try {
      ws = new WebSocket(WS_URL)

      ws.addEventListener('open', () => {
        connected.value = true
        attempts = 0
      })

      ws.addEventListener('message', (event) => {
        try {
          const msg: WsMessage = JSON.parse(event.data)
          handleMessage(msg)
        } catch { /* ignore malformed */ }
      })

      ws.addEventListener('close', () => {
        connected.value = false
        scheduleReconnect()
      })

      ws.addEventListener('error', () => {
        connected.value = false
      })
    } catch {
      scheduleReconnect()
    }
  }

  function handleMessage(msg: WsMessage) {
    const notifications = useNotificationsStore()
    const requests = useRequestsStore()

    switch (msg.type) {
      case 'REQUEST_SUBMITTED': {
        const { title } = msg.payload as { title: string; request_id: string }
        notifications.show(`New request: "${title}"`, 'info')
        requests.fetchList()
        break
      }
      case 'REQUEST_STATUS_CHANGED': {
        const { new_status, request_id } = msg.payload as {
          request_id: string
          new_status: string
        }
        notifications.show(`Request status → ${new_status}`, 'success')
        if (requests.activeRequest?.id === request_id) {
          requests.fetchOne(request_id)
        }
        break
      }
      case 'LAYOUT_AI_APPLIED': {
        const { room_id, item_count } = msg.payload as {
          room_id: string
          item_count: number
        }
        notifications.show(`AI applied layout to room ${room_id} (${item_count} items)`, 'success')
        break
      }
    }
  }

  function scheduleReconnect() {
    if (attempts >= 20) return
    attempts++
    reconnectTimer = setTimeout(connect, 3000)
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    connected.value = false
  }

  return { connected, connect, disconnect }
})
```

---

### `frontend/src/stores/ai.ts`

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { aiApi } from '@/api/ai'
import type { AiMessage } from '@/types'

export const useAiStore = defineStore('ai', () => {
  const messages = ref<AiMessage[]>([])
  const isLoading = ref(false)
  const conversationId = ref<string | null>(null)
  const agentType = ref<string>('copilot')
  const context = ref<object>({})

  function setContext(type: string, ctx: object) {
    agentType.value = type
    context.value = ctx
    // Reset conversation when context changes
    messages.value = []
    conversationId.value = null
  }

  async function sendMessage(content: string) {
    messages.value.push({ role: 'user', content, timestamp: new Date() })
    isLoading.value = true
    try {
      const res = await aiApi.chat({
        message: content,
        agent_type: agentType.value as any,
        context: context.value,
        conversation_id: conversationId.value,
      })
      messages.value.push({
        role: 'assistant',
        content: res.response,
        timestamp: new Date(),
        tool_calls: res.tool_calls_made,
      })
      conversationId.value = res.conversation_id
    } catch (err: any) {
      messages.value.push({
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      })
    } finally {
      isLoading.value = false
    }
  }

  function clearMessages() {
    messages.value = []
    conversationId.value = null
  }

  return {
    messages,
    isLoading,
    conversationId,
    agentType,
    context,
    setContext,
    sendMessage,
    clearMessages,
  }
})
```

---

### `frontend/src/router/index.ts`

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Public
const HomeView = () => import('@/views/public/HomeView.vue')
const VenuesView = () => import('@/views/public/VenuesView.vue')
const BookingView = () => import('@/views/public/BookingView.vue')

// Auth
const LoginView = () => import('@/views/auth/LoginView.vue')
const RegisterView = () => import('@/views/auth/RegisterView.vue')

// Admin
const AdminLayout = () => import('@/components/layout/AdminLayout.vue')
const DashboardView = () => import('@/views/admin/DashboardView.vue')
const RequestsView = () => import('@/views/admin/RequestsView.vue')
const RequestDetailView = () => import('@/views/admin/RequestDetailView.vue')
const InventoryView = () => import('@/views/admin/InventoryView.vue')
const CalendarView = () => import('@/views/admin/CalendarView.vue')
const QuotationsView = () => import('@/views/admin/QuotationsView.vue')
const TasksView = () => import('@/views/admin/TasksView.vue')
const VisualizationView = () => import('@/views/admin/VisualizationView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/venues', component: VenuesView },
    { path: '/book', component: BookingView },
    { path: '/login', component: LoginView, meta: { guestOnly: true } },
    { path: '/register', component: RegisterView, meta: { guestOnly: true } },
    {
      path: '/admin',
      component: AdminLayout,
      meta: { requiresAuth: true, requiresRole: ['admin', 'staff'] },
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', component: DashboardView },
        { path: 'requests', component: RequestsView },
        { path: 'requests/:id', component: RequestDetailView },
        { path: 'inventory', component: InventoryView },
        { path: 'calendar', component: CalendarView },
        { path: 'quotations', component: QuotationsView },
        { path: 'tasks', component: TasksView },
        { path: 'visualization', component: VisualizationView },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.guestOnly && auth.isAuthenticated) {
    return '/admin/dashboard'
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresRole) {
    const allowed = to.meta.requiresRole as string[]
    if (!auth.user || !allowed.includes(auth.user.role)) {
      return '/'
    }
  }
})

export default router
```

---

### `frontend/src/main.ts`

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import '@/assets/styles/base.css'
import '@/assets/styles/utilities.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

---

### `frontend/src/App.vue`

```vue
<template>
  <RouterView />
  <SpToast />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'
import { useAuthStore } from '@/stores/auth'
import SpToast from '@/components/ui/SpToast.vue'

const auth = useAuthStore()
const wsStore = useWebSocketStore()

onMounted(() => {
  if (auth.isStaff) {
    wsStore.connect()
  }
})
</script>
```

---

## Phase F1 — UI Components

### `frontend/src/components/ui/SpButton.vue`

```vue
<template>
  <button
    :class="['sp-btn', `sp-btn--${variant}`, `sp-btn--${size}`, { 'sp-btn--loading': loading }]"
    :disabled="disabled || loading"
    v-bind="$attrs"
  >
    <span v-if="loading" class="sp-btn__spinner" />
    <slot />
  </button>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'accent'
    size?: 'sm' | 'md' | 'lg'
    loading?: boolean
    disabled?: boolean
  }>(),
  { variant: 'primary', size: 'md' },
)
</script>

<style scoped>
.sp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-weight: 500;
  border-radius: var(--radius-md);
  border: 1.5px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  font-family: var(--font-sans);
}
.sp-btn--sm  { padding: 0.35rem 0.75rem; font-size: var(--text-sm); }
.sp-btn--md  { padding: 0.55rem 1.1rem;  font-size: var(--text-sm); }
.sp-btn--lg  { padding: 0.75rem 1.5rem;  font-size: var(--text-base); }

.sp-btn--primary {
  background: var(--accent); color: #fff; border-color: var(--accent);
}
.sp-btn--primary:hover:not(:disabled) { background: var(--accent-hover); border-color: var(--accent-hover); }

.sp-btn--accent {
  background: var(--accent-dark); color: #fff;
}
.sp-btn--accent:hover:not(:disabled) { background: var(--accent); }

.sp-btn--secondary {
  background: var(--surface); color: var(--text-primary);
  border-color: var(--border);
}
.sp-btn--secondary:hover:not(:disabled) { background: var(--surface-hover); }

.sp-btn--ghost {
  background: transparent; color: var(--text-secondary);
}
.sp-btn--ghost:hover:not(:disabled) { background: var(--bg-tertiary); color: var(--text-primary); }

.sp-btn--danger {
  background: var(--error); color: #fff; border-color: var(--error);
}
.sp-btn--danger:hover:not(:disabled) { opacity: 0.88; }

.sp-btn:disabled, .sp-btn--loading { opacity: 0.6; cursor: not-allowed; }

.sp-btn__spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

---

### `frontend/src/components/ui/SpBadge.vue`

```vue
<template>
  <span :class="['sp-badge', `sp-badge--${variant}`]"><slot /></span>
</template>

<script setup lang="ts">
defineProps<{
  variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'accent'
}>()
</script>

<style scoped>
.sp-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.6rem;
  font-size: var(--text-xs);
  font-weight: 600;
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.sp-badge--success { background: var(--success-light); color: var(--success); }
.sp-badge--warning { background: var(--warning-light); color: var(--warning); }
.sp-badge--error   { background: var(--error-light);   color: var(--error);   }
.sp-badge--info,
.sp-badge--accent  { background: var(--accent-light);  color: var(--accent-dark); }
.sp-badge--neutral { background: var(--bg-tertiary);   color: var(--text-secondary); }
</style>
```

---

### `frontend/src/components/ui/SpCard.vue`

```vue
<template>
  <div :class="['sp-card', { 'sp-card--hoverable': hoverable, 'sp-card--selected': selected }]">
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ hoverable?: boolean; selected?: boolean }>()
</script>

<style scoped>
.sp-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-base), border-color var(--transition-base);
}
.sp-card--hoverable:hover { box-shadow: var(--shadow-md); border-color: var(--accent-light); }
.sp-card--selected { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-light); }
</style>
```

---

### `frontend/src/components/ui/SpInput.vue`

```vue
<template>
  <div class="sp-input-wrapper">
    <label v-if="label" :for="inputId" class="sp-input-label">{{ label }}</label>
    <div class="sp-input-field" :class="{ 'sp-input-field--error': error }">
      <span v-if="$slots.prefix" class="sp-input-prefix"><slot name="prefix" /></span>
      <input
        :id="inputId"
        v-bind="$attrs"
        :value="modelValue"
        :type="type"
        :placeholder="placeholder"
        :disabled="disabled"
        class="sp-input-el"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
    </div>
    <p v-if="error" class="sp-input-error">{{ error }}</p>
    <p v-else-if="hint" class="sp-input-hint">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(
  defineProps<{
    modelValue?: string | number
    label?: string
    type?: string
    placeholder?: string
    error?: string
    hint?: string
    disabled?: boolean
  }>(),
  { type: 'text' },
)
defineEmits(['update:modelValue'])
const inputId = computed(() => `sp-input-${Math.random().toString(36).slice(2, 7)}`)
</script>

<style scoped>
.sp-input-wrapper { display: flex; flex-direction: column; gap: var(--space-1); }
.sp-input-label   { font-size: var(--text-sm); font-weight: 500; color: var(--text-primary); }
.sp-input-field   {
  display: flex; align-items: center;
  background: var(--bg-tertiary);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast);
}
.sp-input-field:focus-within { border-color: var(--accent); background: var(--surface); }
.sp-input-field--error { border-color: var(--error); }
.sp-input-prefix { padding: 0 var(--space-3); color: var(--text-tertiary); }
.sp-input-el {
  flex: 1; padding: 0.6rem var(--space-3);
  background: transparent; border: none; outline: none;
  color: var(--text-primary); font-size: var(--text-sm);
  min-width: 0;
}
.sp-input-el::placeholder { color: var(--text-tertiary); }
.sp-input-el:disabled     { opacity: 0.6; cursor: not-allowed; }
.sp-input-error { font-size: var(--text-xs); color: var(--error); }
.sp-input-hint  { font-size: var(--text-xs); color: var(--text-tertiary); }
</style>
```

---

### `frontend/src/components/ui/SpSelect.vue`

```vue
<template>
  <div class="sp-select-wrapper">
    <label v-if="label" class="sp-input-label">{{ label }}</label>
    <select
      :value="modelValue"
      class="sp-select-el"
      :disabled="disabled"
      @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
      <option
        v-for="opt in options"
        :key="typeof opt === 'string' ? opt : opt.value"
        :value="typeof opt === 'string' ? opt : opt.value"
      >{{ typeof opt === 'string' ? opt : opt.label }}</option>
    </select>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue?: string
  label?: string
  placeholder?: string
  options: (string | { value: string; label: string })[]
  disabled?: boolean
}>()
defineEmits(['update:modelValue'])
</script>

<style scoped>
.sp-select-wrapper { display: flex; flex-direction: column; gap: var(--space-1); }
.sp-input-label    { font-size: var(--text-sm); font-weight: 500; color: var(--text-primary); }
.sp-select-el {
  padding: 0.6rem var(--space-3);
  background: var(--bg-tertiary);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  cursor: pointer;
  outline: none;
  transition: border-color var(--transition-fast);
}
.sp-select-el:focus { border-color: var(--accent); background: var(--surface); }
</style>
```

---

### `frontend/src/components/ui/SpModal.vue`

```vue
<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="sp-modal-overlay" @click.self="$emit('update:modelValue', false)">
        <div class="sp-modal" :style="{ maxWidth: width }">
          <div class="sp-modal-header">
            <h3 class="sp-modal-title">{{ title }}</h3>
            <button class="sp-modal-close" @click="$emit('update:modelValue', false)">✕</button>
          </div>
          <div class="sp-modal-body"><slot /></div>
          <div v-if="$slots.footer" class="sp-modal-footer"><slot name="footer" /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{ modelValue: boolean; title: string; width?: string }>(),
  { width: '520px' },
)
defineEmits(['update:modelValue'])
</script>

<style scoped>
.sp-modal-overlay {
  position: fixed; inset: 0; z-index: var(--z-modal);
  background: var(--overlay);
  display: flex; align-items: center; justify-content: center;
  padding: var(--space-4);
}
.sp-modal {
  background: var(--surface); border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg); width: 100%;
  animation: modal-in 0.2s ease;
}
.sp-modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border);
}
.sp-modal-title { font-size: var(--text-lg); font-weight: 600; }
.sp-modal-close {
  width: 32px; height: 32px; border-radius: var(--radius-md);
  border: none; background: transparent;
  color: var(--text-tertiary); font-size: var(--text-base);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: background var(--transition-fast);
}
.sp-modal-close:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.sp-modal-body   { padding: var(--space-6); }
.sp-modal-footer {
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--border);
  display: flex; justify-content: flex-end; gap: var(--space-3);
}
@keyframes modal-in { from { opacity: 0; transform: translateY(-12px) scale(0.97); } }
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
```

---

### `frontend/src/components/ui/SpToast.vue`

```vue
<template>
  <Teleport to="body">
    <div class="sp-toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in notifications.toasts"
          :key="toast.id"
          :class="['sp-toast', `sp-toast--${toast.variant}`]"
        >
          <span class="sp-toast-icon">{{ icons[toast.variant] }}</span>
          <span class="sp-toast-msg">{{ toast.message }}</span>
          <button class="sp-toast-close" @click="notifications.dismiss(toast.id)">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useNotificationsStore } from '@/stores/notifications'
const notifications = useNotificationsStore()
const icons: Record<string, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
}
</script>

<style scoped>
.sp-toast-container {
  position: fixed; bottom: var(--space-6); right: var(--space-6);
  z-index: var(--z-toast);
  display: flex; flex-direction: column; gap: var(--space-2);
  pointer-events: none;
}
.sp-toast {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  font-size: var(--text-sm); font-weight: 500;
  pointer-events: all;
  min-width: 280px; max-width: 420px;
}
.sp-toast--success { background: var(--success); color: #fff; }
.sp-toast--error   { background: var(--error);   color: #fff; }
.sp-toast--warning { background: var(--warning); color: #fff; }
.sp-toast--info    { background: var(--accent);  color: #fff; }
.sp-toast-icon     { font-size: var(--text-base); flex-shrink: 0; }
.sp-toast-msg      { flex: 1; }
.sp-toast-close    {
  background: rgba(255,255,255,0.25); border: none; border-radius: var(--radius-sm);
  color: #fff; cursor: pointer; width: 20px; height: 20px;
  font-size: 11px; display: flex; align-items: center; justify-content: center;
}
.toast-enter-active  { transition: all 0.22s ease; }
.toast-leave-active  { transition: all 0.18s ease; }
.toast-enter-from    { opacity: 0; transform: translateX(24px); }
.toast-leave-to      { opacity: 0; transform: translateX(24px); }
</style>
```

---

### `frontend/src/components/ui/SpSpinner.vue`

```vue
<template>
  <div class="sp-spinner" :style="{ width: size + 'px', height: size + 'px' }" />
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 24 })
</script>

<style scoped>
.sp-spinner {
  border: 2.5px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

---

## Phase F1 — Layout Components

### `frontend/src/components/layout/AppNav.vue`

```vue
<template>
  <nav class="app-nav">
    <div class="page-container app-nav__inner">
      <RouterLink to="/" class="app-nav__brand">
        <span class="app-nav__logo">⬡</span>
        <span class="app-nav__name">SpaceFlow</span>
      </RouterLink>
      <div class="app-nav__links">
        <RouterLink to="/venues" class="app-nav__link">Venues</RouterLink>
        <RouterLink to="/book" class="app-nav__link">Book a Space</RouterLink>
        <template v-if="auth.isAuthenticated">
          <RouterLink v-if="auth.isStaff" to="/admin/dashboard" class="app-nav__link">Admin</RouterLink>
          <SpButton size="sm" variant="ghost" @click="auth.logout(); $router.push('/login')">
            Sign Out
          </SpButton>
        </template>
        <template v-else>
          <RouterLink to="/login">
            <SpButton size="sm" variant="ghost">Sign In</SpButton>
          </RouterLink>
          <RouterLink to="/register">
            <SpButton size="sm" variant="primary">Get Started</SpButton>
          </RouterLink>
        </template>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import SpButton from '@/components/ui/SpButton.vue'
const auth = useAuthStore()
</script>

<style scoped>
.app-nav {
  position: sticky; top: 0; z-index: var(--z-nav);
  background: var(--nav-bg);
  border-bottom: 1px solid var(--nav-border);
  backdrop-filter: blur(12px);
}
.app-nav__inner {
  display: flex; align-items: center; justify-content: space-between;
  height: 64px;
}
.app-nav__brand {
  display: flex; align-items: center; gap: var(--space-2);
  text-decoration: none;
}
.app-nav__logo { font-size: 1.5rem; color: var(--accent); }
.app-nav__name { font-size: var(--text-xl); font-weight: 700; color: var(--text-primary); }
.app-nav__links { display: flex; align-items: center; gap: var(--space-2); }
.app-nav__link {
  font-size: var(--text-sm); font-weight: 500; color: var(--text-secondary);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  transition: color var(--transition-fast), background var(--transition-fast);
  text-decoration: none;
}
.app-nav__link:hover,
.app-nav__link.router-link-active { color: var(--accent); background: var(--accent-light); }
</style>
```

---

### `frontend/src/components/layout/AdminSidebar.vue`

```vue
<template>
  <aside class="admin-sidebar" :class="{ 'admin-sidebar--collapsed': collapsed }">
    <div class="admin-sidebar__brand">
      <span class="admin-sidebar__logo">⬡</span>
      <span v-if="!collapsed" class="admin-sidebar__name">SpaceFlow</span>
      <button class="admin-sidebar__toggle" @click="collapsed = !collapsed">
        {{ collapsed ? '→' : '←' }}
      </button>
    </div>
    <nav class="admin-sidebar__nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="admin-sidebar__item"
        active-class="admin-sidebar__item--active"
      >
        <span class="admin-sidebar__icon">{{ item.icon }}</span>
        <span v-if="!collapsed" class="admin-sidebar__label">{{ item.label }}</span>
        <SpBadge
          v-if="!collapsed && item.badge"
          variant="error"
          style="margin-left: auto; font-size: 10px; padding: 1px 5px;"
        >{{ item.badge }}</SpBadge>
      </RouterLink>
    </nav>
    <div v-if="!collapsed" class="admin-sidebar__user">
      <div class="admin-sidebar__avatar">{{ auth.user?.full_name?.charAt(0) ?? 'U' }}</div>
      <div class="admin-sidebar__user-info">
        <span class="admin-sidebar__user-name">{{ auth.user?.full_name }}</span>
        <span class="admin-sidebar__user-role">{{ auth.user?.role }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import SpBadge from '@/components/ui/SpBadge.vue'
const auth = useAuthStore()
const collapsed = ref(false)
const navItems = [
  { to: '/admin/dashboard',     label: 'Dashboard',      icon: '◉' },
  { to: '/admin/requests',      label: 'Requests',       icon: '📋' },
  { to: '/admin/inventory',     label: 'Inventory',      icon: '📦' },
  { to: '/admin/calendar',      label: 'Calendar',       icon: '📅' },
  { to: '/admin/quotations',    label: 'Quotations',     icon: '💶' },
  { to: '/admin/tasks',         label: 'Tasks',          icon: '✓' },
  { to: '/admin/visualization', label: '3D View',        icon: '🏛' },
]
</script>

<style scoped>
.admin-sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  position: fixed; left: 0; top: 0;
  z-index: var(--z-sidebar);
  transition: width var(--transition-base);
  overflow: hidden;
}
.admin-sidebar--collapsed { width: var(--sidebar-collapsed); }

.admin-sidebar__brand {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-4) var(--space-4);
  border-bottom: 1px solid var(--border);
  min-height: var(--topbar-height);
}
.admin-sidebar__logo { font-size: 1.5rem; color: var(--accent); flex-shrink: 0; }
.admin-sidebar__name { font-weight: 700; color: var(--text-primary); white-space: nowrap; }
.admin-sidebar__toggle {
  margin-left: auto; width: 24px; height: 24px;
  border: none; background: transparent; cursor: pointer;
  color: var(--text-tertiary); border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}
.admin-sidebar__toggle:hover { background: var(--bg-tertiary); }

.admin-sidebar__nav { flex: 1; padding: var(--space-3) var(--space-2); overflow-y: auto; }
.admin-sidebar__item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  margin-bottom: 2px;
  text-decoration: none;
  color: var(--text-secondary);
  font-size: var(--text-sm); font-weight: 500;
  transition: all var(--transition-fast);
  white-space: nowrap;
}
.admin-sidebar__item:hover { background: var(--bg-secondary); color: var(--text-primary); }
.admin-sidebar__item--active { background: var(--accent-light); color: var(--accent-dark); }
.admin-sidebar__icon { font-size: 1rem; flex-shrink: 0; width: 20px; text-align: center; }

.admin-sidebar__user {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-4);
  border-top: 1px solid var(--border);
}
.admin-sidebar__avatar {
  width: 32px; height: 32px; border-radius: var(--radius-full);
  background: var(--accent-light); color: var(--accent-dark);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: var(--text-sm); flex-shrink: 0;
}
.admin-sidebar__user-info { display: flex; flex-direction: column; min-width: 0; }
.admin-sidebar__user-name { font-size: var(--text-sm); font-weight: 600; color: var(--text-primary); truncate: true; }
.admin-sidebar__user-role { font-size: var(--text-xs); color: var(--text-tertiary); text-transform: capitalize; }
</style>
```

---

### `frontend/src/components/layout/AdminLayout.vue`

```vue
<template>
  <div class="admin-layout">
    <AdminSidebar />
    <div class="admin-main" :class="{ 'admin-main--full': !wsStore.connected }">
      <header class="admin-topbar">
        <div class="admin-topbar__left">
          <h1 class="admin-topbar__title">{{ pageTitle }}</h1>
        </div>
        <div class="admin-topbar__right">
          <div
            class="ws-indicator"
            :class="wsStore.connected ? 'ws-indicator--online' : 'ws-indicator--offline'"
            :title="wsStore.connected ? 'Live updates active' : 'Offline — reconnecting'"
          >
            <span class="ws-dot" />
            <span class="ws-label">{{ wsStore.connected ? 'Live' : 'Offline' }}</span>
          </div>
          <button class="ai-fab" title="Open AI Copilot" @click="showAiPanel = !showAiPanel">
            ✦ AI
          </button>
        </div>
      </header>
      <main class="admin-content">
        <RouterView />
      </main>
    </div>

    <!-- Global AI Copilot Panel -->
    <AiChatPanel v-model="showAiPanel" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useWebSocketStore } from '@/stores/websocket'
import AdminSidebar from './AdminSidebar.vue'
import AiChatPanel from '@/components/ai/AiChatPanel.vue'

const route = useRoute()
const wsStore = useWebSocketStore()
const showAiPanel = ref(false)

const titleMap: Record<string, string> = {
  '/admin/dashboard': 'Dashboard',
  '/admin/requests': 'Event Requests',
  '/admin/inventory': 'Inventory',
  '/admin/calendar': 'Calendar',
  '/admin/quotations': 'Quotations',
  '/admin/tasks': 'Task Board',
  '/admin/visualization': '3D Visualization',
}
const pageTitle = computed(() => {
  if (route.path.includes('/admin/requests/') && route.params.id) return 'Request Detail'
  return titleMap[route.path] ?? 'Admin'
})
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; background: var(--bg-secondary); }
.admin-main {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex; flex-direction: column;
  min-height: 100vh;
  transition: margin-left var(--transition-base);
}
.admin-topbar {
  height: var(--topbar-height);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 var(--space-6);
  position: sticky; top: 0; z-index: 40;
}
.admin-topbar__title { font-size: var(--text-xl); font-weight: 700; }
.admin-topbar__right { display: flex; align-items: center; gap: var(--space-4); }

.ws-indicator {
  display: flex; align-items: center; gap: var(--space-2);
  padding: 0.25rem var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: 500;
}
.ws-indicator--online  { background: var(--success-light); color: var(--success); }
.ws-indicator--offline { background: var(--warning-light); color: var(--warning); }
.ws-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: currentColor;
  animation: pulse 1.8s ease-in-out infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.ai-fab {
  background: var(--accent); color: #fff;
  border: none; border-radius: var(--radius-md);
  padding: 0.4rem 0.9rem;
  font-size: var(--text-sm); font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.ai-fab:hover { background: var(--accent-hover); }
.admin-content { flex: 1; padding: var(--space-6); }
</style>
```

---

## Phase F2 — Public Booking Portal

### `frontend/src/views/public/HomeView.vue`

```vue
<template>
  <div class="home">
    <AppNav />

    <!-- Hero -->
    <section class="hero">
      <div class="page-container hero__inner">
        <div class="hero__text">
          <SpBadge variant="accent">Pyramid of Tirana — Albania</SpBadge>
          <h1 class="hero__heading">Book Your Event<br>at the Pyramid</h1>
          <p class="hero__sub">
            Albania's most iconic venue. Five distinct spaces, AI-assisted booking,
            real-time availability — all in one platform.
          </p>
          <div class="hero__ctas">
            <RouterLink to="/book">
              <SpButton size="lg" variant="primary">Submit a Request</SpButton>
            </RouterLink>
            <RouterLink to="/venues">
              <SpButton size="lg" variant="secondary">Browse Spaces</SpButton>
            </RouterLink>
          </div>
        </div>
        <div class="hero__visual">
          <div class="hero__pyramid-badge">
            <span class="hero__pyramid-icon">🏛</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Stats -->
    <section class="stats-bar">
      <div class="page-container stats-bar__inner">
        <div v-for="stat in stats" :key="stat.label" class="stat-item">
          <span class="stat-item__value">{{ stat.value }}</span>
          <span class="stat-item__label">{{ stat.label }}</span>
        </div>
      </div>
    </section>

    <!-- Venues Grid -->
    <section class="section venues-section">
      <div class="page-container">
        <h2 class="section-title">Our Spaces</h2>
        <p class="section-sub">Five unique rooms across two floors of the Pyramid</p>
        <div class="venues-grid" v-if="!loading">
          <SpCard
            v-for="venue in venues"
            :key="venue.id"
            hoverable
            class="venue-card"
          >
            <div class="venue-card__color-bar" :style="{ background: venueColor(venue.name) }" />
            <h3 class="venue-card__name">{{ venue.name }}</h3>
            <p class="venue-card__cap">Up to {{ venue.capacity_max }} guests</p>
            <p class="venue-card__desc">{{ venue.description ?? 'A versatile event space in the Pyramid.' }}</p>
            <RouterLink :to="`/book?venue=${venue.id}`">
              <SpButton size="sm" variant="secondary" class="w-full" style="margin-top: var(--space-4)">
                Check Availability
              </SpButton>
            </RouterLink>
          </SpCard>
        </div>
        <div v-else class="flex justify-center"><SpSpinner :size="36" /></div>
      </div>
    </section>

    <!-- How It Works -->
    <section class="section how-section" style="background: var(--bg-secondary);">
      <div class="page-container">
        <h2 class="section-title">How It Works</h2>
        <div class="how-steps">
          <div v-for="(step, i) in steps" :key="i" class="how-step">
            <div class="how-step__number">{{ i + 1 }}</div>
            <h4 class="how-step__title">{{ step.title }}</h4>
            <p class="how-step__desc">{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="page-container footer__inner">
        <span>Pyramid of Tirana • Powered by SpaceFlow</span>
        <span>JunctionX Tirana 2026</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { venuesApi } from '@/api/venues'
import type { Venue } from '@/types'
import AppNav from '@/components/layout/AppNav.vue'
import SpBadge from '@/components/ui/SpBadge.vue'
import SpButton from '@/components/ui/SpButton.vue'
import SpCard from '@/components/ui/SpCard.vue'
import SpSpinner from '@/components/ui/SpSpinner.vue'

const venues = ref<Venue[]>([])
const loading = ref(true)

onMounted(async () => {
  try { venues.value = (await venuesApi.list()).items } catch { /* ignore */ }
  finally { loading.value = false }
})

const venueColorMap: Record<string, string> = {
  'blue': '#3da9f5', 'orange': '#ff6400',
  'green': '#2ec98a', 'yellow': '#f5a623', 'corridor': '#9b59b6',
}
function venueColor(name: string) {
  const key = Object.keys(venueColorMap).find((k) => name.toLowerCase().includes(k))
  return key ? venueColorMap[key] : '#3da9f5'
}

const stats = [
  { value: '5', label: 'Unique Spaces' },
  { value: '400+', label: 'Events Hosted' },
  { value: '5,000+', label: 'Happy Guests' },
  { value: '24h', label: 'AI Response Time' },
]
const steps = [
  { title: 'Submit Request',    desc: 'Fill the booking form with your event details, date, and requirements.' },
  { title: 'AI Analysis',       desc: 'Our AI checks availability, matches the ideal space, and flags any conflicts.' },
  { title: 'Get Quotation',     desc: 'Receive an itemised cost estimate with venue, equipment, and service fees.' },
  { title: 'Confirm & Plan',    desc: 'Approve the booking. We auto-generate the operational task plan.' },
]
</script>

<style scoped>
/* Hero */
.hero { background: linear-gradient(160deg, var(--hero-gradient-start) 30%, var(--hero-gradient-end) 100%); padding: var(--space-16) 0 var(--space-12); }
.hero__inner { display: flex; align-items: center; justify-content: space-between; gap: var(--space-8); }
.hero__text  { max-width: 560px; }
.hero__heading { font-size: clamp(2rem, 5vw, 3.25rem); font-weight: 700; line-height: 1.15; margin: var(--space-4) 0 var(--space-4); }
.hero__sub   { font-size: var(--text-lg); color: var(--text-secondary); margin-bottom: var(--space-8); }
.hero__ctas  { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.hero__visual { flex-shrink: 0; }
.hero__pyramid-badge {
  width: 200px; height: 200px; border-radius: var(--radius-2xl);
  background: var(--accent-light);
  display: flex; align-items: center; justify-content: center;
}
.hero__pyramid-icon { font-size: 6rem; }

/* Stats */
.stats-bar { background: var(--accent); padding: var(--space-6) 0; }
.stats-bar__inner { display: flex; justify-content: space-around; flex-wrap: wrap; gap: var(--space-4); }
.stat-item { text-align: center; color: #fff; }
.stat-item__value { display: block; font-size: var(--text-3xl); font-weight: 700; }
.stat-item__label { font-size: var(--text-sm); opacity: 0.85; }

/* Venues */
.section-title { font-size: var(--text-3xl); font-weight: 700; text-align: center; margin-bottom: var(--space-2); }
.section-sub   { text-align: center; color: var(--text-secondary); margin-bottom: var(--space-10); }
.venues-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-5); }
.venue-card { display: flex; flex-direction: column; overflow: hidden; padding: 0; }
.venue-card__color-bar { height: 5px; }
.venue-card > * { padding: 0 var(--space-5); }
.venue-card__color-bar { padding: 0; }
.venue-card__name { font-size: var(--text-lg); font-weight: 700; margin-top: var(--space-4); padding-top: var(--space-4); }
.venue-card__cap  { font-size: var(--text-sm); color: var(--text-secondary); margin-top: var(--space-1); }
.venue-card__desc { font-size: var(--text-sm); color: var(--text-tertiary); margin-top: var(--space-2); flex: 1; }
.venue-card > :last-child { padding-bottom: var(--space-4); }

/* How */
.how-steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--space-8); margin-top: var(--space-8); }
.how-step { text-align: center; }
.how-step__number {
  width: 44px; height: 44px; border-radius: var(--radius-full);
  background: var(--accent); color: #fff;
  font-size: var(--text-lg); font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto var(--space-3);
}
.how-step__title { font-weight: 600; margin-bottom: var(--space-2); }
.how-step__desc  { font-size: var(--text-sm); color: var(--text-secondary); }

/* Footer */
.footer { background: var(--text-primary); color: var(--bg-secondary); padding: var(--space-6) 0; }
.footer__inner { display: flex; justify-content: space-between; font-size: var(--text-sm); }
</style>
```

---

### `frontend/src/views/public/BookingView.vue`

```vue
<template>
  <div class="booking-page">
    <AppNav />
    <div class="page-container" style="padding-top: var(--space-10); padding-bottom: var(--space-16);">
      <div class="booking-header">
        <h2>Submit an Event Request</h2>
        <p>Fill in the details below. Our AI will analyse your request and propose the best space and quotation.</p>
      </div>

      <!-- Step indicator -->
      <div class="step-indicator">
        <div v-for="(s, i) in stepLabels" :key="i"
          :class="['step-dot', { 'step-dot--active': step === i, 'step-dot--done': step > i }]">
          <span class="step-dot__num">{{ step > i ? '✓' : i + 1 }}</span>
          <span class="step-dot__label">{{ s }}</span>
        </div>
      </div>

      <div class="booking-form-card">
        <!-- Step 1: Event Details -->
        <div v-if="step === 0">
          <h3 class="form-section-title">Event Details</h3>
          <div class="form-grid">
            <SpInput v-model="form.title" label="Event Title *" placeholder="e.g. AlbTech Annual Summit 2026" />
            <SpSelect
              v-model="form.event_type"
              label="Event Type *"
              :options="eventTypeOptions"
              placeholder="Select type..."
            />
            <SpInput v-model.number="form.attendee_count" label="Expected Attendees *" type="number" placeholder="e.g. 120" />
            <SpInput v-model="form.requested_date" label="Event Date *" type="date" />
            <SpInput v-model="form.start_time" label="Start Time *" type="time" />
            <SpInput v-model="form.end_time" label="End Time *" type="time" />
          </div>
          <div class="form-full-row" style="margin-top: var(--space-4);">
            <SpInput
              v-model="form.description"
              label="Description"
              placeholder="Brief overview of your event..."
            />
          </div>
        </div>

        <!-- Step 2: Space & Requirements -->
        <div v-else-if="step === 1">
          <h3 class="form-section-title">Space & Requirements</h3>
          <div v-if="loadingVenues" class="flex justify-center p-4"><SpSpinner :size="32" /></div>
          <div v-else class="venue-select-grid">
            <div
              v-for="venue in venues"
              :key="venue.id"
              :class="['venue-option', { 'venue-option--selected': form.venue_id === venue.id }]"
              @click="form.venue_id = venue.id"
            >
              <div class="venue-option__bar" :style="{ background: venueColor(venue.name) }" />
              <div class="venue-option__body">
                <span class="venue-option__name">{{ venue.name }}</span>
                <span class="venue-option__cap">Up to {{ venue.capacity_max }} guests</span>
              </div>
              <span v-if="form.venue_id === venue.id" class="venue-option__check">✓</span>
            </div>
          </div>
          <div style="margin-top: var(--space-6);">
            <label class="sp-input-label" style="margin-bottom: var(--space-2); display:block;">
              Special Requirements
            </label>
            <textarea
              v-model="form.special_requirements"
              rows="4"
              placeholder="e.g. Need 3 wireless microphones, 1 projector, coffee break tables..."
              class="sp-textarea"
            />
          </div>
        </div>

        <!-- Step 3: Review & Submit -->
        <div v-else>
          <h3 class="form-section-title">Review & Submit</h3>
          <div class="review-card">
            <div class="review-row"><span>Title</span><strong>{{ form.title }}</strong></div>
            <div class="review-row"><span>Type</span><strong>{{ form.event_type }}</strong></div>
            <div class="review-row"><span>Attendees</span><strong>{{ form.attendee_count }}</strong></div>
            <div class="review-row"><span>Date</span><strong>{{ form.requested_date }}</strong></div>
            <div class="review-row"><span>Time</span><strong>{{ form.start_time }} – {{ form.end_time }}</strong></div>
            <div class="review-row" v-if="selectedVenue"><span>Venue</span><strong>{{ selectedVenue.name }}</strong></div>
          </div>
          <p class="review-note">
            After submission, our AI will immediately analyse your request and prepare a venue recommendation
            and cost estimate. You'll see the proposal in real time from your request status page.
          </p>
        </div>

        <!-- Navigation buttons -->
        <div class="form-nav">
          <SpButton v-if="step > 0" variant="secondary" @click="step--">← Back</SpButton>
          <span v-else />
          <SpButton
            v-if="step < 2"
            variant="primary"
            :disabled="!canProceed"
            @click="step++"
          >
            Continue →
          </SpButton>
          <SpButton
            v-else
            variant="primary"
            :loading="submitting"
            @click="submitRequest"
          >
            Submit Request
          </SpButton>
        </div>
      </div>

      <!-- Success screen -->
      <div v-if="submitted" class="success-screen">
        <div class="success-icon">✓</div>
        <h3>Request Submitted!</h3>
        <p>Our AI is analysing your request now. You'll receive a proposal shortly.</p>
        <SpButton variant="primary" @click="$router.push('/')">Back to Home</SpButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { venuesApi } from '@/api/venues'
import { requestsApi } from '@/api/requests'
import { useNotificationsStore } from '@/stores/notifications'
import type { Venue } from '@/types'
import AppNav from '@/components/layout/AppNav.vue'
import SpButton from '@/components/ui/SpButton.vue'
import SpInput from '@/components/ui/SpInput.vue'
import SpSelect from '@/components/ui/SpSelect.vue'
import SpSpinner from '@/components/ui/SpSpinner.vue'

const route = useRoute()
const notifications = useNotificationsStore()

const step = ref(0)
const submitting = ref(false)
const submitted = ref(false)
const venues = ref<Venue[]>([])
const loadingVenues = ref(true)
const stepLabels = ['Event Details', 'Space & Requirements', 'Review & Submit']

const form = ref({
  title: '',
  event_type: '' as any,
  attendee_count: 0,
  requested_date: '',
  start_time: '',
  end_time: '',
  description: '',
  venue_id: route.query.venue as string ?? '',
  special_requirements: '',
})

const eventTypeOptions = [
  { value: 'conference',  label: 'Conference' },
  { value: 'workshop',    label: 'Workshop' },
  { value: 'concert',     label: 'Concert' },
  { value: 'exhibition',  label: 'Exhibition' },
  { value: 'hackathon',   label: 'Hackathon' },
  { value: 'dinner',      label: 'Dinner' },
  { value: 'other',       label: 'Other' },
]

const selectedVenue = computed(() => venues.value.find((v) => v.id === form.value.venue_id))

const canProceed = computed(() => {
  if (step.value === 0) {
    return form.value.title && form.value.event_type && form.value.attendee_count > 0 &&
           form.value.requested_date && form.value.start_time && form.value.end_time
  }
  return true
})

const venueColorMap: Record<string, string> = {
  blue: '#3da9f5', orange: '#ff6400', green: '#2ec98a', yellow: '#f5a623',
}
function venueColor(name: string) {
  const key = Object.keys(venueColorMap).find((k) => name.toLowerCase().includes(k))
  return key ? venueColorMap[key] : '#3da9f5'
}

onMounted(async () => {
  try { venues.value = (await venuesApi.list()).items } catch { /* ignore */ }
  finally { loadingVenues.value = false }
})

async function submitRequest() {
  submitting.value = true
  try {
    await requestsApi.create({
      title: form.value.title,
      event_type: form.value.event_type,
      attendee_count: form.value.attendee_count,
      requested_date: form.value.requested_date,
      start_time: form.value.start_time + ':00',
      end_time: form.value.end_time + ':00',
      description: form.value.description || undefined,
      venue_id: form.value.venue_id || undefined,
      special_requirements: form.value.special_requirements || undefined,
    })
    submitted.value = true
  } catch (err: any) {
    notifications.show(err.response?.data?.detail ?? 'Submission failed', 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.booking-header { text-align: center; margin-bottom: var(--space-8); }
.booking-header p { color: var(--text-secondary); margin-top: var(--space-2); }

.step-indicator {
  display: flex; justify-content: center; gap: var(--space-8);
  margin-bottom: var(--space-8);
}
.step-dot { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); }
.step-dot__num {
  width: 36px; height: 36px; border-radius: 50%;
  border: 2px solid var(--border);
  background: var(--surface);
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: var(--text-sm);
  color: var(--text-tertiary);
  transition: all var(--transition-fast);
}
.step-dot--active .step-dot__num { border-color: var(--accent); color: var(--accent); }
.step-dot--done   .step-dot__num { border-color: var(--success); background: var(--success); color: #fff; }
.step-dot__label  { font-size: var(--text-xs); color: var(--text-tertiary); }

.booking-form-card {
  max-width: 680px; margin: 0 auto;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-xl); padding: var(--space-8);
  box-shadow: var(--shadow-md);
}
.form-section-title { font-size: var(--text-xl); font-weight: 600; margin-bottom: var(--space-6); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
.form-full-row { grid-column: 1 / -1; }
.sp-textarea {
  width: 100%; padding: var(--space-3);
  background: var(--bg-tertiary); border: 1.5px solid var(--border);
  border-radius: var(--radius-md); font-family: var(--font-sans);
  font-size: var(--text-sm); color: var(--text-primary);
  resize: vertical; outline: none;
  transition: border-color var(--transition-fast);
}
.sp-textarea:focus { border-color: var(--accent); background: var(--surface); }

.venue-select-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); }
.venue-option {
  display: flex; align-items: center; gap: var(--space-3);
  border: 1.5px solid var(--border); border-radius: var(--radius-lg);
  overflow: hidden; cursor: pointer;
  transition: all var(--transition-fast);
}
.venue-option:hover { border-color: var(--accent-light); background: var(--surface-hover); }
.venue-option--selected { border-color: var(--accent); background: var(--accent-light); }
.venue-option__bar { width: 5px; align-self: stretch; flex-shrink: 0; }
.venue-option__body { flex: 1; padding: var(--space-3) 0; }
.venue-option__name { display: block; font-weight: 600; font-size: var(--text-sm); }
.venue-option__cap  { display: block; font-size: var(--text-xs); color: var(--text-tertiary); }
.venue-option__check { padding-right: var(--space-3); color: var(--accent); font-weight: 700; }

.review-card { border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; margin-bottom: var(--space-4); }
.review-row {
  display: flex; justify-content: space-between; padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm); border-bottom: 1px solid var(--border-light);
}
.review-row:last-child { border-bottom: none; }
.review-row span { color: var(--text-secondary); }
.review-note { font-size: var(--text-sm); color: var(--text-secondary); text-align: center; }

.form-nav { display: flex; justify-content: space-between; align-items: center; margin-top: var(--space-8); }

.success-screen { text-align: center; padding: var(--space-12); }
.success-icon {
  width: 64px; height: 64px; border-radius: 50%;
  background: var(--success); color: #fff;
  font-size: 2rem; display: flex; align-items: center; justify-content: center;
  margin: 0 auto var(--space-4);
}
.success-screen h3 { font-size: var(--text-2xl); margin-bottom: var(--space-2); }
.success-screen p { color: var(--text-secondary); margin-bottom: var(--space-6); }
</style>
```

---

## Phase F3 — Authentication Flow

### `frontend/src/views/auth/LoginView.vue`

```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <RouterLink to="/" class="auth-brand">
        <span class="auth-brand__icon">⬡</span>
        <span class="auth-brand__name">SpaceFlow</span>
      </RouterLink>
      <h2 class="auth-title">Sign in to your account</h2>
      <form @submit.prevent="handleLogin" class="auth-form">
        <SpInput v-model="email" label="Email address" type="email" placeholder="you@example.com" :error="fieldError('email')" />
        <SpInput v-model="password" label="Password" type="password" placeholder="••••••••" :error="fieldError('password')" />
        <div v-if="auth.error" class="auth-error">{{ auth.error }}</div>
        <SpButton type="submit" variant="primary" size="lg" :loading="auth.loading" class="w-full">
          Sign In
        </SpButton>
      </form>
      <p class="auth-footer">
        Don't have an account?
        <RouterLink to="/register" class="auth-link">Create one →</RouterLink>
      </p>
      <!-- Demo credentials hint -->
      <div class="auth-demo">
        <strong>Demo:</strong> admin@spaceflo.dev / Admin1234!
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWebSocketStore } from '@/stores/websocket'
import SpInput from '@/components/ui/SpInput.vue'
import SpButton from '@/components/ui/SpButton.vue'

const router = useRouter()
const auth = useAuthStore()
const wsStore = useWebSocketStore()
const email = ref('')
const password = ref('')
const errors = ref<Record<string, string>>({})

function fieldError(field: string) { return errors.value[field] }

async function handleLogin() {
  errors.value = {}
  if (!email.value) { errors.value.email = 'Email is required'; return }
  if (!password.value) { errors.value.password = 'Password is required'; return }
  const user = await auth.login({ email: email.value, password: password.value }).catch(() => null)
  if (user) {
    if (user.role === 'admin' || user.role === 'staff') {
      wsStore.connect()
      router.push('/admin/dashboard')
    } else {
      router.push('/')
    }
  }
}
</script>

<style scoped>
.auth-page { min-height: 100vh; background: var(--bg-secondary); display: flex; align-items: center; justify-content: center; padding: var(--space-4); }
.auth-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-2xl); padding: var(--space-10); width: 100%; max-width: 420px; box-shadow: var(--shadow-lg); }
.auth-brand { display: flex; align-items: center; gap: var(--space-2); text-decoration: none; justify-content: center; margin-bottom: var(--space-6); }
.auth-brand__icon { font-size: 1.75rem; color: var(--accent); }
.auth-brand__name { font-size: var(--text-xl); font-weight: 700; color: var(--text-primary); }
.auth-title { font-size: var(--text-2xl); font-weight: 700; text-align: center; margin-bottom: var(--space-6); }
.auth-form { display: flex; flex-direction: column; gap: var(--space-4); }
.auth-error { background: var(--error-light); color: var(--error); font-size: var(--text-sm); padding: var(--space-3); border-radius: var(--radius-md); }
.auth-footer { text-align: center; font-size: var(--text-sm); color: var(--text-secondary); margin-top: var(--space-4); }
.auth-link { color: var(--accent); font-weight: 500; }
.auth-demo { margin-top: var(--space-4); padding: var(--space-3); background: var(--bg-tertiary); border-radius: var(--radius-md); font-size: var(--text-xs); text-align: center; color: var(--text-secondary); }
</style>
```

---

### `frontend/src/views/auth/RegisterView.vue`

```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <RouterLink to="/" class="auth-brand">
        <span class="auth-brand__icon">⬡</span>
        <span class="auth-brand__name">SpaceFlow</span>
      </RouterLink>
      <h2 class="auth-title">Create an account</h2>
      <form @submit.prevent="handleRegister" class="auth-form">
        <SpInput v-model="form.full_name" label="Full Name *" placeholder="Your full name" />
        <SpInput v-model="form.email" label="Email address *" type="email" placeholder="you@example.com" />
        <SpInput v-model="form.password" label="Password *" type="password" placeholder="At least 8 characters" />
        <div v-if="auth.error" class="auth-error">{{ auth.error }}</div>
        <SpButton type="submit" variant="primary" size="lg" :loading="auth.loading" class="w-full">
          Create Account
        </SpButton>
      </form>
      <p class="auth-footer">
        Already have an account?
        <RouterLink to="/login" class="auth-link">Sign in →</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import SpInput from '@/components/ui/SpInput.vue'
import SpButton from '@/components/ui/SpButton.vue'

const router = useRouter()
const auth = useAuthStore()
const form = ref({ full_name: '', email: '', password: '' })

async function handleRegister() {
  const user = await auth.register(form.value).catch(() => null)
  if (user) router.push('/')
}
</script>

<style scoped>
.auth-page { min-height: 100vh; background: var(--bg-secondary); display: flex; align-items: center; justify-content: center; padding: var(--space-4); }
.auth-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-2xl); padding: var(--space-10); width: 100%; max-width: 420px; box-shadow: var(--shadow-lg); }
.auth-brand { display: flex; align-items: center; gap: var(--space-2); text-decoration: none; justify-content: center; margin-bottom: var(--space-6); }
.auth-brand__icon { font-size: 1.75rem; color: var(--accent); }
.auth-brand__name { font-size: var(--text-xl); font-weight: 700; color: var(--text-primary); }
.auth-title { font-size: var(--text-2xl); font-weight: 700; text-align: center; margin-bottom: var(--space-6); }
.auth-form { display: flex; flex-direction: column; gap: var(--space-4); }
.auth-error { background: var(--error-light); color: var(--error); font-size: var(--text-sm); padding: var(--space-3); border-radius: var(--radius-md); }
.auth-footer { text-align: center; font-size: var(--text-sm); color: var(--text-secondary); margin-top: var(--space-4); }
.auth-link { color: var(--accent); font-weight: 500; }
</style>
```

---

## Phase F4 — Admin: Requests & Pipeline

### `frontend/src/components/requests/RequestStatusBadge.vue`

```vue
<template>
  <SpBadge :variant="variantMap[status] ?? 'neutral'">{{ labelMap[status] ?? status }}</SpBadge>
</template>

<script setup lang="ts">
import type { RequestStatus } from '@/types'
import SpBadge from '@/components/ui/SpBadge.vue'
defineProps<{ status: RequestStatus }>()
const variantMap: Record<string, string> = {
  submitted:    'info',
  under_review: 'warning',
  pending_info: 'warning',
  approved:     'success',
  rejected:     'error',
  completed:    'neutral',
  cancelled:    'error',
}
const labelMap: Record<string, string> = {
  submitted:    'Submitted',
  under_review: 'Under Review',
  pending_info: 'Pending Info',
  approved:     'Approved',
  rejected:     'Rejected',
  completed:    'Completed',
  cancelled:    'Cancelled',
}
</script>
```

---

### `frontend/src/components/requests/RequestCard.vue`

```vue
<template>
  <SpCard hoverable class="request-card" @click="$router.push(`/admin/requests/${request.id}`)">
    <div class="request-card__header">
      <RequestStatusBadge :status="request.status" />
      <span class="request-card__date">{{ formatDate(request.requested_date) }}</span>
    </div>
    <h3 class="request-card__title">{{ request.title }}</h3>
    <div class="request-card__meta">
      <span>{{ request.attendee_count }} attendees</span>
      <span v-if="request.venue">· {{ request.venue.name }}</span>
      <span v-if="request.client">· {{ request.client.full_name }}</span>
    </div>
    <div class="request-card__footer">
      <span
        v-if="request.has_ai_proposal"
        class="ai-badge"
        :class="request.has_conflicts ? 'ai-badge--conflict' : 'ai-badge--ok'"
      >
        {{ request.has_conflicts ? '⚠ Conflicts' : '✓ AI Ready' }}
      </span>
      <span v-else class="ai-badge ai-badge--pending">⏳ Analysing...</span>
      <div class="request-card__actions" @click.stop>
        <SpButton size="sm" variant="secondary" @click="$router.push(`/admin/requests/${request.id}`)">
          Review
        </SpButton>
      </div>
    </div>
  </SpCard>
</template>

<script setup lang="ts">
import type { EventRequestSummary } from '@/types'
import SpCard from '@/components/ui/SpCard.vue'
import SpButton from '@/components/ui/SpButton.vue'
import RequestStatusBadge from './RequestStatusBadge.vue'

defineProps<{ request: EventRequestSummary }>()
function formatDate(d: string) { return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) }
</script>

<style scoped>
.request-card { cursor: pointer; padding: var(--space-4) var(--space-5); }
.request-card__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
.request-card__date { font-size: var(--text-xs); color: var(--text-tertiary); }
.request-card__title { font-size: var(--text-base); font-weight: 600; margin-bottom: var(--space-1); }
.request-card__meta { font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-3); }
.request-card__footer { display: flex; align-items: center; justify-content: space-between; }
.ai-badge { font-size: var(--text-xs); font-weight: 600; padding: 2px 8px; border-radius: var(--radius-full); }
.ai-badge--ok       { background: var(--success-light); color: var(--success); }
.ai-badge--conflict { background: var(--warning-light); color: var(--warning); }
.ai-badge--pending  { background: var(--bg-tertiary);   color: var(--text-tertiary); }
</style>
```

---

### `frontend/src/views/admin/RequestsView.vue`

```vue
<template>
  <div class="requests-view">
    <!-- Filters -->
    <div class="requests-toolbar">
      <div class="status-tabs">
        <button
          v-for="tab in statusTabs"
          :key="tab.value"
          :class="['status-tab', { 'status-tab--active': activeStatus === tab.value }]"
          @click="setStatus(tab.value)"
        >
          {{ tab.label }}
          <span v-if="tab.value === activeStatus && store.total > 0" class="status-tab__count">
            {{ store.total }}
          </span>
        </button>
      </div>
      <div class="requests-toolbar__right">
        <SpInput v-model="search" placeholder="Search requests..." style="width: 240px;">
          <template #prefix>🔍</template>
        </SpInput>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="requests-empty">
      <SpSpinner :size="40" />
    </div>

    <!-- Empty state -->
    <div v-else-if="filtered.length === 0" class="requests-empty">
      <p>No requests found for this filter.</p>
    </div>

    <!-- Request cards -->
    <div v-else class="requests-grid">
      <TransitionGroup name="list">
        <RequestCard
          v-for="req in filtered"
          :key="req.id"
          :request="req"
        />
      </TransitionGroup>
    </div>

    <!-- Pagination -->
    <div v-if="store.total > pageSize" class="pagination">
      <SpButton size="sm" variant="secondary" :disabled="page === 0" @click="page--; load()">← Prev</SpButton>
      <span class="pagination__info">{{ page * pageSize + 1 }}–{{ Math.min((page + 1) * pageSize, store.total) }} of {{ store.total }}</span>
      <SpButton size="sm" variant="secondary" :disabled="(page + 1) * pageSize >= store.total" @click="page++; load()">Next →</SpButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRequestsStore } from '@/stores/requests'
import RequestCard from '@/components/requests/RequestCard.vue'
import SpInput from '@/components/ui/SpInput.vue'
import SpButton from '@/components/ui/SpButton.vue'
import SpSpinner from '@/components/ui/SpSpinner.vue'

const store = useRequestsStore()
const page = ref(0)
const pageSize = 20
const activeStatus = ref('')
const search = ref('')

const statusTabs = [
  { value: '',             label: 'All' },
  { value: 'submitted',    label: 'Submitted' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'approved',     label: 'Approved' },
  { value: 'completed',    label: 'Completed' },
  { value: 'rejected',     label: 'Rejected' },
]

const filtered = computed(() => {
  if (!search.value) return store.items
  const q = search.value.toLowerCase()
  return store.items.filter(
    (r) => r.title.toLowerCase().includes(q) || r.client?.full_name?.toLowerCase().includes(q),
  )
})

function setStatus(status: string) {
  activeStatus.value = status
  page.value = 0
  load()
}

async function load() {
  await store.fetchList({
    status: activeStatus.value || undefined,
    limit: pageSize,
    offset: page.value * pageSize,
  })
}

onMounted(load)
</script>

<style scoped>
.requests-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-6); flex-wrap: wrap; gap: var(--space-3);
}
.status-tabs  { display: flex; gap: var(--space-1); flex-wrap: wrap; }
.status-tab   {
  padding: 0.4rem 0.9rem; font-size: var(--text-sm); font-weight: 500;
  border: 1.5px solid var(--border); border-radius: var(--radius-full);
  background: var(--surface); color: var(--text-secondary); cursor: pointer;
  transition: all var(--transition-fast); display: flex; align-items: center; gap: var(--space-2);
}
.status-tab:hover         { border-color: var(--accent-light); color: var(--accent); }
.status-tab--active       { background: var(--accent); border-color: var(--accent); color: #fff; }
.status-tab__count        { background: rgba(255,255,255,0.3); border-radius: var(--radius-full); padding: 0 6px; font-size: 11px; }
.requests-toolbar__right  { display: flex; align-items: center; gap: var(--space-3); }
.requests-grid            { display: flex; flex-direction: column; gap: var(--space-3); }
.requests-empty           { text-align: center; padding: var(--space-16); color: var(--text-tertiary); }
.pagination               { display: flex; align-items: center; justify-content: center; gap: var(--space-4); margin-top: var(--space-6); }
.pagination__info         { font-size: var(--text-sm); color: var(--text-secondary); }
.list-enter-active        { transition: all 0.25s ease; }
.list-enter-from          { opacity: 0; transform: translateY(-8px); }
</style>
```

---

### `frontend/src/views/admin/RequestDetailView.vue`

```vue
<template>
  <div v-if="store.loading" class="flex justify-center" style="padding: var(--space-16);">
    <SpSpinner :size="48" />
  </div>
  <div v-else-if="!req" class="empty-state">Request not found.</div>
  <div v-else class="request-detail">
    <!-- Header -->
    <div class="req-header">
      <div class="req-header__left">
        <RouterLink to="/admin/requests" class="back-link">← Requests</RouterLink>
        <h2 class="req-header__title">{{ req.title }}</h2>
        <div class="req-header__meta">
          <RequestStatusBadge :status="req.status" />
          <span class="text-muted">· {{ req.event_type }} · {{ req.attendee_count }} attendees · {{ req.requested_date }}</span>
        </div>
      </div>
      <div class="req-header__actions">
        <SpButton
          v-if="req.status === 'submitted' || req.status === 'under_review'"
          variant="primary"
          :loading="actioning"
          @click="approveRequest"
        >
          ✓ Approve
        </SpButton>
        <SpButton
          v-if="['submitted','under_review','approved'].includes(req.status)"
          variant="danger"
          :loading="actioning"
          @click="showRejectModal = true"
        >
          Reject
        </SpButton>
        <SpButton variant="secondary" @click="aiStore.setContext('copilot', { request_id: req.id }); showAiPanel = true">
          ✦ Ask AI
        </SpButton>
      </div>
    </div>

    <!-- Tabs -->
    <div class="req-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['req-tab', { 'req-tab--active': activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span v-if="tab.badge" class="req-tab__badge">{{ tab.badge }}</span>
      </button>
    </div>

    <!-- Tab: Overview -->
    <div v-if="activeTab === 'overview'" class="tab-content">
      <div class="overview-grid">
        <SpCard>
          <h4 class="card-section-title">Request Details</h4>
          <table class="detail-table">
            <tbody>
              <tr><td>Client</td><td>{{ req.client?.full_name ?? '—' }}</td></tr>
              <tr><td>Organization</td><td>{{ req.client?.organization ?? '—' }}</td></tr>
              <tr><td>Date</td><td>{{ req.requested_date }}</td></tr>
              <tr><td>Time</td><td>{{ req.start_time }} – {{ req.end_time }}</td></tr>
              <tr><td>Attendees</td><td>{{ req.attendee_count }}</td></tr>
              <tr><td>Venue</td><td>{{ req.venue?.name ?? 'Not assigned' }}</td></tr>
              <tr v-if="req.special_requirements"><td>Requirements</td><td>{{ req.special_requirements }}</td></tr>
            </tbody>
          </table>
        </SpCard>

        <!-- AI Proposal Card -->
        <div v-if="req.ai_proposal_json">
          <AiProposalCard :proposal="req.ai_proposal_json" />
        </div>
        <div v-else class="ai-pending-card">
          <SpSpinner :size="20" />
          <span>AI is analysing this request…</span>
        </div>
      </div>
    </div>

    <!-- Tab: Conflicts -->
    <div v-if="activeTab === 'conflicts'" class="tab-content">
      <div v-if="conflicts.length === 0" class="empty-state success-state">
        <span class="success-icon-sm">✓</span> No conflicts detected for this request.
      </div>
      <ConflictAlert v-for="(c, i) in conflicts" :key="i" :conflict="c" />
      <div class="tab-actions">
        <SpButton variant="secondary" :loading="rerunningConflicts" @click="rerunConflicts">
          ↻ Re-run Conflict Check
        </SpButton>
      </div>
    </div>

    <!-- Tab: Tasks -->
    <div v-if="activeTab === 'tasks'" class="tab-content">
      <div v-if="tasks.length === 0" class="empty-state">
        <p>No tasks generated yet.</p>
        <SpButton variant="primary" :loading="generatingTasks" @click="generateTasks" style="margin-top: var(--space-4);">
          ✦ Generate Task List with AI
        </SpButton>
      </div>
      <div v-else>
        <div class="tasks-header">
          <span class="text-muted">{{ tasks.length }} tasks</span>
          <SpButton size="sm" variant="ghost" :loading="generatingTasks" @click="generateTasks">↻ Regenerate</SpButton>
        </div>
        <div class="tasks-list">
          <div v-for="task in tasks" :key="task.id" class="task-row">
            <span :class="['task-priority', `task-priority--${priorityLabel(task.priority)}`]" />
            <span class="task-type-badge">{{ task.task_type }}</span>
            <span class="task-title">{{ task.title }}</span>
            <span class="task-due text-muted">{{ formatDue(task.due_at) }}</span>
            <SpBadge :variant="statusVariant(task.status)">{{ task.status }}</SpBadge>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab: 3D Room -->
    <div v-if="activeTab === '3d'" class="tab-content">
      <div class="three-d-tab">
        <ThreeDFrame :room-id="req.venue?.three_d_room_id ?? undefined" />
        <SpButton
          class="ai-design-btn"
          variant="primary"
          @click="aiStore.setContext('room_designer', { venue_name: req.venue?.name, event_request_id: req.id }); showAiPanel = true"
        >
          ✦ AI Design Room
        </SpButton>
      </div>
    </div>
  </div>

  <!-- Reject Modal -->
  <SpModal v-model="showRejectModal" title="Reject Request">
    <SpInput v-model="rejectReason" label="Rejection reason" placeholder="Please provide a reason..." />
    <template #footer>
      <SpButton variant="secondary" @click="showRejectModal = false">Cancel</SpButton>
      <SpButton variant="danger" :loading="actioning" @click="rejectRequest">Confirm Rejection</SpButton>
    </template>
  </SpModal>

  <!-- AI Panel (context-aware) -->
  <AiChatPanel v-model="showAiPanel" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRequestsStore } from '@/stores/requests'
import { useAiStore } from '@/stores/ai'
import { useNotificationsStore } from '@/stores/notifications'
import { requestsApi } from '@/api/requests'
import { tasksApi } from '@/api/tasks'
import { aiApi } from '@/api/ai'
import type { Task, Conflict } from '@/types'
import SpCard from '@/components/ui/SpCard.vue'
import SpButton from '@/components/ui/SpButton.vue'
import SpBadge from '@/components/ui/SpBadge.vue'
import SpInput from '@/components/ui/SpInput.vue'
import SpModal from '@/components/ui/SpModal.vue'
import SpSpinner from '@/components/ui/SpSpinner.vue'
import RequestStatusBadge from '@/components/requests/RequestStatusBadge.vue'
import ConflictAlert from '@/components/requests/ConflictAlert.vue'
import AiProposalCard from '@/components/requests/AiProposalCard.vue'
import ThreeDFrame from '@/components/visualization/ThreeDFrame.vue'
import AiChatPanel from '@/components/ai/AiChatPanel.vue'

const route = useRoute()
const store = useRequestsStore()
const aiStore = useAiStore()
const notifications = useNotificationsStore()

const req = computed(() => store.activeRequest)
const activeTab = ref('overview')
const tasks = ref<Task[]>([])
const conflicts = ref<Conflict[]>([])
const actioning = ref(false)
const generatingTasks = ref(false)
const rerunningConflicts = ref(false)
const showRejectModal = ref(false)
const showAiPanel = ref(false)
const rejectReason = ref('')

const tabs = computed(() => [
  { key: 'overview',  label: 'Overview' },
  { key: 'conflicts', label: 'Conflicts', badge: conflicts.value.length > 0 ? conflicts.value.length : undefined },
  { key: 'tasks',     label: 'Tasks', badge: tasks.value.length > 0 ? tasks.value.length : undefined },
  { key: '3d',        label: '3D Room' },
])

onMounted(async () => {
  const id = route.params.id as string
  await store.fetchOne(id)
  if (req.value) {
    loadConflicts()
    loadTasks()
  }
})

async function loadConflicts() {
  try {
    const res = await requestsApi.conflicts(req.value!.id)
    conflicts.value = res.conflicts ?? []
  } catch { /* ignore */ }
}

async function loadTasks() {
  try {
    const res = await tasksApi.list({ request_id: req.value!.id })
    tasks.value = res.items ?? res
  } catch { /* ignore */ }
}

async function approveRequest() {
  actioning.value = true
  try {
    await requestsApi.approve(req.value!.id)
    await store.fetchOne(req.value!.id)
    notifications.show('Request approved', 'success')
  } catch (e: any) {
    notifications.show(e.response?.data?.detail ?? 'Approval failed', 'error')
  } finally {
    actioning.value = false
  }
}

async function rejectRequest() {
  actioning.value = true
  try {
    await requestsApi.reject(req.value!.id, rejectReason.value)
    await store.fetchOne(req.value!.id)
    showRejectModal.value = false
    notifications.show('Request rejected', 'info')
  } catch { /* ignore */ }
  finally { actioning.value = false }
}

async function generateTasks() {
  generatingTasks.value = true
  try {
    await tasksApi.generate(req.value!.id)
    await loadTasks()
    notifications.show('Task list generated', 'success')
  } catch { /* ignore */ }
  finally { generatingTasks.value = false }
}

async function rerunConflicts() {
  rerunningConflicts.value = true
  try {
    await aiApi.detectConflicts(req.value!.id)
    await loadConflicts()
    notifications.show('Conflict check complete', 'success')
  } catch { /* ignore */ }
  finally { rerunningConflicts.value = false }
}

function priorityLabel(p: number) { return p === 1 ? 'high' : p === 2 ? 'medium' : 'low' }
function statusVariant(s: string) {
  return { pending: 'warning', in_progress: 'info', blocked: 'error', done: 'success', cancelled: 'neutral' }[s] ?? 'neutral' as any
}
function formatDue(dt: string) { return new Date(dt).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' }) }
</script>

<style scoped>
.request-detail { max-width: 1000px; }
.req-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: var(--space-6); gap: var(--space-4); flex-wrap: wrap; }
.back-link { font-size: var(--text-sm); color: var(--text-secondary); display: block; margin-bottom: var(--space-2); }
.req-header__title { font-size: var(--text-2xl); font-weight: 700; margin-bottom: var(--space-2); }
.req-header__meta  { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); }
.req-header__actions { display: flex; gap: var(--space-2); flex-wrap: wrap; align-items: flex-start; }

.req-tabs { display: flex; gap: var(--space-1); border-bottom: 1px solid var(--border); margin-bottom: var(--space-6); }
.req-tab {
  padding: var(--space-3) var(--space-4); font-size: var(--text-sm); font-weight: 500;
  color: var(--text-secondary); background: transparent; border: none;
  border-bottom: 2px solid transparent; cursor: pointer;
  transition: all var(--transition-fast); display: flex; align-items: center; gap: var(--space-2);
}
.req-tab:hover         { color: var(--text-primary); }
.req-tab--active       { color: var(--accent); border-bottom-color: var(--accent); }
.req-tab__badge        {
  background: var(--error); color: #fff; font-size: 10px; font-weight: 700;
  padding: 1px 5px; border-radius: var(--radius-full); min-width: 16px; text-align: center;
}

.tab-content { animation: fade-in 0.15s ease; }
@keyframes fade-in { from { opacity: 0; transform: translateY(4px); } }

.overview-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-6); }
.card-section-title { font-size: var(--text-base); font-weight: 600; margin-bottom: var(--space-4); }
.detail-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.detail-table td { padding: var(--space-2) 0; border-bottom: 1px solid var(--border-light); }
.detail-table td:first-child { color: var(--text-secondary); width: 40%; }
.detail-table td:last-child { font-weight: 500; }

.ai-pending-card {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-5); background: var(--bg-tertiary);
  border-radius: var(--radius-lg); color: var(--text-secondary);
  font-size: var(--text-sm);
}

.empty-state { text-align: center; padding: var(--space-10); color: var(--text-tertiary); }
.success-state { color: var(--success); display: flex; align-items: center; justify-content: center; gap: var(--space-2); }
.success-icon-sm { font-size: 1.2rem; font-weight: 700; }

.tab-actions { margin-top: var(--space-4); }

.tasks-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-3); }
.tasks-list   { display: flex; flex-direction: column; gap: var(--space-2); }
.task-row {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-md); font-size: var(--text-sm);
}
.task-priority { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.task-priority--high   { background: var(--error); }
.task-priority--medium { background: var(--warning); }
.task-priority--low    { background: var(--success); }
.task-type-badge {
  background: var(--bg-tertiary); color: var(--text-secondary);
  font-size: var(--text-xs); font-weight: 600; padding: 2px 8px;
  border-radius: var(--radius-full); text-transform: uppercase; flex-shrink: 0;
}
.task-title { flex: 1; font-weight: 500; }
.task-due   { font-size: var(--text-xs); }

.three-d-tab { position: relative; }
.ai-design-btn { position: absolute; top: var(--space-4); right: var(--space-4); z-index: 10; }
</style>
```

---

### `frontend/src/components/requests/AiProposalCard.vue`

```vue
<template>
  <SpCard class="ai-proposal-card">
    <div class="ai-proposal-card__header">
      <span class="ai-icon">✦</span>
      <h4>AI Proposal</h4>
      <SpBadge :variant="proposal.status === 'complete' ? 'success' : 'warning'">
        {{ proposal.status === 'complete' ? 'Ready' : 'Processing' }}
      </SpBadge>
    </div>
    <p v-if="proposal.summary" class="ai-summary">{{ proposal.summary?.substring(0, 280) }}{{ proposal.summary?.length > 280 ? '…' : '' }}</p>
    <div v-if="proposal.recommended_venue" class="ai-venue-rec">
      <span class="ai-label">Recommended venue:</span>
      <strong>{{ proposal.recommended_venue.name ?? 'None found' }}</strong>
    </div>
    <div v-if="proposal.estimate" class="ai-estimate">
      <div class="ai-estimate-row">
        <span>Estimated total</span>
        <strong class="ai-estimate-total">€ {{ proposal.estimate.total.toFixed(2) }}</strong>
      </div>
      <div class="ai-estimate-row text-muted">
        <span>Subtotal</span><span>€ {{ proposal.estimate.subtotal.toFixed(2) }}</span>
      </div>
      <div class="ai-estimate-row text-muted">
        <span>Tax (20%)</span><span>€ {{ proposal.estimate.tax.toFixed(2) }}</span>
      </div>
    </div>
    <div v-if="proposal.conflicts && proposal.conflicts.length > 0" class="ai-conflicts-summary">
      <SpBadge variant="warning">{{ proposal.conflicts.length }} conflict{{ proposal.conflicts.length > 1 ? 's' : '' }}</SpBadge>
    </div>
  </SpCard>
</template>

<script setup lang="ts">
import type { AiProposal } from '@/types'
import SpCard from '@/components/ui/SpCard.vue'
import SpBadge from '@/components/ui/SpBadge.vue'
defineProps<{ proposal: AiProposal }>()
</script>

<style scoped>
.ai-proposal-card { border-left: 3px solid var(--accent); }
.ai-proposal-card__header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-4); }
.ai-icon { font-size: 1.1rem; color: var(--accent); }
.ai-proposal-card__header h4 { flex: 1; font-weight: 600; }
.ai-summary { font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-4); }
.ai-venue-rec { font-size: var(--text-sm); margin-bottom: var(--space-4); }
.ai-label { color: var(--text-secondary); margin-right: var(--space-2); }
.ai-estimate { border-top: 1px solid var(--border); padding-top: var(--space-3); }
.ai-estimate-row { display: flex; justify-content: space-between; font-size: var(--text-sm); padding: var(--space-1) 0; }
.ai-estimate-total { font-size: var(--text-lg); color: var(--accent-dark); }
.ai-conflicts-summary { margin-top: var(--space-3); }
</style>
```

---

### `frontend/src/components/requests/ConflictAlert.vue`

```vue
<template>
  <div :class="['conflict-alert', `conflict-alert--${conflict.severity}`]">
    <div class="conflict-alert__icon">{{ conflict.severity === 'blocking' ? '🚫' : '⚠️' }}</div>
    <div class="conflict-alert__body">
      <div class="conflict-alert__header">
        <SpBadge :variant="conflict.severity === 'blocking' ? 'error' : 'warning'">
          {{ conflict.severity === 'blocking' ? 'Blocking' : 'Warning' }}
        </SpBadge>
        <span class="conflict-alert__type">{{ conflict.type }}</span>
      </div>
      <p class="conflict-alert__desc">{{ conflict.description }}</p>
      <p class="conflict-alert__suggestion"><strong>Suggestion:</strong> {{ conflict.suggestion }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Conflict } from '@/types'
import SpBadge from '@/components/ui/SpBadge.vue'
defineProps<{ conflict: Conflict }>()
</script>

<style scoped>
.conflict-alert {
  display: flex; gap: var(--space-4);
  padding: var(--space-4); border-radius: var(--radius-lg);
  margin-bottom: var(--space-3);
}
.conflict-alert--blocking { background: var(--error-light); border-left: 4px solid var(--error); }
.conflict-alert--warning  { background: var(--warning-light); border-left: 4px solid var(--warning); }
.conflict-alert__icon  { font-size: 1.4rem; flex-shrink: 0; }
.conflict-alert__header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.conflict-alert__type  { font-size: var(--text-sm); font-weight: 600; color: var(--text-primary); }
.conflict-alert__desc  { font-size: var(--text-sm); color: var(--text-primary); margin-bottom: var(--space-1); }
.conflict-alert__suggestion { font-size: var(--text-sm); color: var(--text-secondary); }
</style>
```

---

## Phase F5 — Admin: Inventory Management

### `frontend/src/components/inventory/AssetAvailabilityBar.vue`

```vue
<template>
  <div class="avail-bar">
    <div class="avail-bar__track">
      <div
        class="avail-bar__fill"
        :style="{ width: pct + '%', background: fillColor }"
      />
    </div>
    <span class="avail-bar__label">{{ available }}/{{ total }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ available: number; total: number }>()
const pct = computed(() => props.total > 0 ? Math.round((props.available / props.total) * 100) : 0)
const fillColor = computed(() => {
  if (pct.value > 60) return 'var(--success)'
  if (pct.value > 30) return 'var(--warning)'
  return 'var(--error)'
})
</script>

<style scoped>
.avail-bar { display: flex; align-items: center; gap: var(--space-3); }
.avail-bar__track { flex: 1; height: 6px; background: var(--bg-tertiary); border-radius: var(--radius-full); overflow: hidden; }
.avail-bar__fill  { height: 100%; border-radius: var(--radius-full); transition: width 0.4s ease; }
.avail-bar__label { font-size: var(--text-xs); font-weight: 600; color: var(--text-secondary); white-space: nowrap; min-width: 52px; text-align: right; }
</style>
```

---

### `frontend/src/views/admin/InventoryView.vue`

```vue
<template>
  <div class="inventory-view">
    <!-- Summary stats -->
    <div class="inventory-stats">
      <SpCard v-for="stat in stats" :key="stat.label" class="stat-card">
        <div class="stat-card__value">{{ stat.value }}</div>
        <div class="stat-card__label">{{ stat.label }}</div>
      </SpCard>
    </div>

    <!-- Category tabs -->
    <div class="category-tabs">
      <button
        v-for="cat in categories"
        :key="cat.value"
        :class="['cat-tab', { 'cat-tab--active': activeCategory === cat.value }]"
        @click="activeCategory = cat.value"
      >
        {{ cat.label }}
      </button>
    </div>

    <!-- Asset grid -->
    <div v-if="store.loading" class="flex justify-center" style="padding: var(--space-10);"><SpSpinner :size="40" /></div>
    <div v-else class="asset-grid">
      <SpCard
        v-for="asset in filteredAssets"
        :key="asset.id"
        hoverable
        class="asset-card"
      >
        <div class="asset-card__header">
          <span class="asset-card__name">{{ asset.name }}</span>
          <SpBadge variant="neutral">{{ asset.category }}</SpBadge>
        </div>
        <div class="asset-card__count">
          <span class="asset-card__available">{{ asset.total_quantity }}</span>
          <span class="asset-card__unit">units total</span>
        </div>
        <AssetAvailabilityBar :available="asset.total_quantity" :total="asset.total_quantity" style="margin-top: var(--space-3);" />
        <div class="asset-card__footer">
          <span class="text-muted" style="font-size: var(--text-xs);">€{{ Number(asset.unit_price).toFixed(2) }}/unit</span>
          <span v-if="asset.three_d_item_key" class="asset-card__3d-badge">3D: {{ asset.three_d_item_key }}</span>
        </div>
      </SpCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAssetsStore } from '@/stores/assets'
import SpCard from '@/components/ui/SpCard.vue'
import SpBadge from '@/components/ui/SpBadge.vue'
import SpSpinner from '@/components/ui/SpSpinner.vue'
import AssetAvailabilityBar from '@/components/inventory/AssetAvailabilityBar.vue'

const store = useAssetsStore()
const activeCategory = ref('')

const categories = [
  { value: '',          label: 'All' },
  { value: 'seating',   label: 'Seating' },
  { value: 'tables',    label: 'Tables' },
  { value: 'av_equipment', label: 'AV Equipment' },
  { value: 'staging',   label: 'Staging' },
  { value: 'misc',      label: 'Misc' },
]

const filteredAssets = computed(() =>
  activeCategory.value
    ? store.items.filter((a) => a.category === activeCategory.value)
    : store.items,
)

const stats = computed(() => [
  { label: 'Asset Types',   value: store.items.length },
  { label: 'Total Units',   value: store.items.reduce((s, a) => s + a.total_quantity, 0) },
  { label: 'Active',        value: store.items.filter((a) => a.is_active).length },
  { label: '3D-Linked',     value: store.items.filter((a) => !!a.three_d_item_key).length },
])

onMounted(() => store.fetchAll())
</script>

<style scoped>
.inventory-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); margin-bottom: var(--space-6); }
.stat-card       { text-align: center; padding: var(--space-5); }
.stat-card__value { font-size: var(--text-3xl); font-weight: 700; color: var(--accent); }
.stat-card__label { font-size: var(--text-sm); color: var(--text-secondary); margin-top: var(--space-1); }

.category-tabs { display: flex; gap: var(--space-2); margin-bottom: var(--space-5); flex-wrap: wrap; }
.cat-tab {
  padding: 0.4rem 1rem; font-size: var(--text-sm); font-weight: 500;
  border: 1.5px solid var(--border); border-radius: var(--radius-full);
  background: var(--surface); color: var(--text-secondary); cursor: pointer;
  transition: all var(--transition-fast);
}
.cat-tab:hover       { border-color: var(--accent-light); color: var(--accent); }
.cat-tab--active     { background: var(--accent); border-color: var(--accent); color: #fff; }

.asset-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: var(--space-4); }
.asset-card { }
.asset-card__header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-2); margin-bottom: var(--space-2); }
.asset-card__name   { font-weight: 600; font-size: var(--text-base); }
.asset-card__count  { display: flex; align-items: baseline; gap: var(--space-1); }
.asset-card__available { font-size: var(--text-3xl); font-weight: 700; color: var(--text-primary); }
.asset-card__unit   { font-size: var(--text-sm); color: var(--text-secondary); }
.asset-card__footer { display: flex; justify-content: space-between; align-items: center; margin-top: var(--space-3); }
.asset-card__3d-badge {
  font-size: var(--text-xs); background: var(--accent-light); color: var(--accent-dark);
  padding: 2px 8px; border-radius: var(--radius-full); font-weight: 600;
}
</style>
```

---

## Phase F6 — Admin: Calendar

### `frontend/src/views/admin/CalendarView.vue`

```vue
<template>
  <div class="calendar-view">
    <div class="calendar-toolbar">
      <div class="venue-filters">
        <label
          v-for="v in venueFilters"
          :key="v.label"
          class="venue-filter-chip"
        >
          <input type="checkbox" v-model="v.active" style="display:none;">
          <span
            class="venue-filter-dot"
            :style="{ background: v.active ? v.color : 'var(--border)' }"
          />
          <span :style="{ color: v.active ? v.color : 'var(--text-tertiary)' }">{{ v.label }}</span>
        </label>
      </div>
    </div>

    <SpCard style="padding: 0; overflow: hidden;">
      <FullCalendar :options="calendarOptions" />
    </SpCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import { requestsApi } from '@/api/requests'
import { useRouter } from 'vue-router'
import SpCard from '@/components/ui/SpCard.vue'

const router = useRouter()

const venueFilters = ref([
  { label: 'Blue Room',   color: '#3da9f5', active: true },
  { label: 'Orange Room', color: '#ff6400', active: true },
  { label: 'Green Room',  color: '#2ec98a', active: true },
  { label: 'Yellow Room', color: '#f5a623', active: true },
])

function venueColor(venueName: string) {
  if (!venueName) return '#7a9bb5'
  const lower = venueName.toLowerCase()
  if (lower.includes('blue'))   return '#3da9f5'
  if (lower.includes('orange')) return '#ff6400'
  if (lower.includes('green'))  return '#2ec98a'
  if (lower.includes('yellow')) return '#f5a623'
  return '#7a9bb5'
}

const calendarOptions = computed(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay',
  },
  slotMinTime: '07:00:00',
  slotMaxTime: '23:00:00',
  height: 'auto',
  events: async (info: any, successCallback: Function) => {
    try {
      const res = await requestsApi.list({ status: 'approved', limit: 200 })
      const events = res.items.map((r) => ({
        id: r.id,
        title: `${r.title} (${r.attendee_count})`,
        start: `${r.requested_date}T${r.start_time}`,
        end: `${r.requested_date}T${r.end_time}`,
        backgroundColor: venueColor(r.venue?.name ?? ''),
        borderColor: r.has_conflicts ? '#f04848' : 'transparent',
        extendedProps: r,
      }))
      successCallback(events)
    } catch {
      successCallback([])
    }
  },
  eventClick: ({ event }: any) => {
    router.push(`/admin/requests/${event.id}`)
  },
  eventContent: ({ event }: any) => ({
    html: `<div class="fc-event-custom">
      <div class="fc-title">${event.title}</div>
      ${event.extendedProps.venue ? `<div class="fc-venue">${event.extendedProps.venue.name}</div>` : ''}
    </div>`,
  }),
}))
</script>

<style scoped>
.calendar-toolbar { display: flex; align-items: center; margin-bottom: var(--space-4); }
.venue-filters { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.venue-filter-chip {
  display: flex; align-items: center; gap: var(--space-2);
  cursor: pointer; font-size: var(--text-sm);
  padding: var(--space-1) var(--space-3);
  border: 1.5px solid var(--border); border-radius: var(--radius-full);
  transition: all var(--transition-fast);
}
.venue-filter-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; transition: background 0.2s; }
</style>

<style>
/* Global FullCalendar custom styles */
.fc-event-custom   { padding: 2px 4px; font-size: 12px; }
.fc-title          { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fc-venue          { font-size: 11px; opacity: 0.85; }
.fc .fc-toolbar-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); }
.fc .fc-button     { background: var(--surface) !important; border: 1.5px solid var(--border) !important; color: var(--text-primary) !important; font-size: 0.85rem !important; font-family: var(--font-sans) !important; }
.fc .fc-button-active { background: var(--accent) !important; color: #fff !important; border-color: var(--accent) !important; }
.fc .fc-col-header-cell-cushion { font-weight: 600; color: var(--text-secondary); font-size: 0.8rem; }
</style>
```

---

## Phase F7 — Admin: Quotations

### `frontend/src/views/admin/QuotationsView.vue`

```vue
<template>
  <div class="quotations-view">
    <div class="quotations-toolbar">
      <div class="status-tabs">
        <button
          v-for="tab in tabs"
          :key="tab"
          :class="['status-tab', { 'status-tab--active': activeTab === tab }]"
          @click="activeTab = tab"
        >{{ tab }}</button>
      </div>
    </div>

    <SpCard style="padding: 0; overflow: hidden;">
      <table class="quotations-table">
        <thead>
          <tr>
            <th>Event</th><th>Client</th><th>Date</th>
            <th>Amount</th><th>Status</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="req in pipelineRequests"
            :key="req.id"
            class="quotations-row"
            @click="$router.push(`/admin/requests/${req.id}`)"
          >
            <td class="quotations-title">{{ req.title }}</td>
            <td>{{ req.client?.full_name ?? '—' }}</td>
            <td>{{ req.requested_date }}</td>
            <td>
              <strong v-if="req.ai_proposal_json?.estimate">
                € {{ req.ai_proposal_json.estimate.total.toFixed(2) }}
              </strong>
              <span v-else class="text-muted">—</span>
            </td>
            <td><RequestStatusBadge :status="req.status" /></td>
            <td @click.stop>
              <SpButton size="sm" variant="ghost" @click="$router.push(`/admin/requests/${req.id}`)">
                View
              </SpButton>
            </td>
          </tr>
          <tr v-if="pipelineRequests.length === 0">
            <td colspan="6" style="text-align: center; padding: var(--space-8); color: var(--text-tertiary);">
              No quotations found.
            </td>
          </tr>
        </tbody>
      </table>
    </SpCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRequestsStore } from '@/stores/requests'
import SpCard from '@/components/ui/SpCard.vue'
import SpButton from '@/components/ui/SpButton.vue'
import RequestStatusBadge from '@/components/requests/RequestStatusBadge.vue'
import type { EventRequestSummary } from '@/types'

const store = useRequestsStore()
const activeTab = ref('All')
const tabs = ['All', 'Draft', 'Sent', 'Approved', 'Rejected']

const pipelineRequests = computed<(EventRequestSummary & { ai_proposal_json?: any })[]>(() => {
  return store.items
})

onMounted(() => store.fetchList({ limit: 100 }))
</script>

<style scoped>
.quotations-toolbar { margin-bottom: var(--space-5); }
.status-tabs { display: flex; gap: var(--space-2); }
.status-tab {
  padding: 0.4rem 1rem; font-size: var(--text-sm); font-weight: 500;
  border: 1.5px solid var(--border); border-radius: var(--radius-full);
  background: var(--surface); color: var(--text-secondary); cursor: pointer;
  transition: all var(--transition-fast);
}
.status-tab:hover     { border-color: var(--accent-light); color: var(--accent); }
.status-tab--active   { background: var(--accent); border-color: var(--accent); color: #fff; }

.quotations-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.quotations-table thead th {
  padding: var(--space-3) var(--space-4);
  text-align: left; font-size: var(--text-xs); font-weight: 600;
  color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em;
  background: var(--bg-secondary); border-bottom: 1px solid var(--border);
}
.quotations-row { cursor: pointer; transition: background var(--transition-fast); }
.quotations-row:hover { background: var(--surface-hover); }
.quotations-row td { padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--border-light); }
.quotations-title { font-weight: 600; }
</style>
```

---

## Phase F8 — Admin: Task Board

### `frontend/src/views/admin/TasksView.vue`

```vue
<template>
  <div class="tasks-view">
    <div class="kanban-board">
      <div
        v-for="col in columns"
        :key="col.key"
        class="kanban-col"
      >
        <div class="kanban-col__header">
          <span class="kanban-col__title">{{ col.label }}</span>
          <span class="kanban-col__count">{{ tasksInCol(col.key).length }}</span>
        </div>
        <div class="kanban-col__body">
          <div
            v-if="store.loading"
            class="flex justify-center"
            style="padding: var(--space-6);"
          >
            <SpSpinner :size="28" />
          </div>
          <div
            v-for="task in tasksInCol(col.key)"
            :key="task.id"
            class="task-card"
            @click="openTask(task)"
          >
            <div class="task-card__header">
              <span :class="['task-prio', `task-prio--${prioCls(task.priority)}`]" />
              <span class="task-type">{{ taskTypeIcon(task.task_type) }} {{ task.task_type }}</span>
            </div>
            <p class="task-card__title">{{ task.title }}</p>
            <div class="task-card__footer">
              <span class="task-due">{{ formatDue(task.due_at) }}</span>
              <SpBadge v-if="task.ai_generated" variant="info" style="font-size:10px;">AI</SpBadge>
            </div>
          </div>
          <div v-if="!store.loading && tasksInCol(col.key).length === 0" class="kanban-empty">
            No tasks
          </div>
        </div>
      </div>
    </div>

    <!-- Task Detail Modal -->
    <SpModal v-model="showModal" :title="activeTask?.title ?? 'Task Detail'" width="580px">
      <div v-if="activeTask" class="task-detail">
        <div class="detail-row"><span>Type</span><strong>{{ activeTask.task_type }}</strong></div>
        <div class="detail-row"><span>Status</span>
          <SpSelect v-model="editStatus" :options="statusOptions" style="width:160px;" @update:modelValue="updateStatus" />
        </div>
        <div class="detail-row"><span>Priority</span><strong>{{ ['', 'High', 'Medium', 'Low'][activeTask.priority] }}</strong></div>
        <div class="detail-row"><span>Due</span><strong>{{ formatDue(activeTask.due_at) }}</strong></div>
        <div v-if="activeTask.description" class="detail-desc">{{ activeTask.description }}</div>
      </div>
    </SpModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { tasksApi } from '@/api/tasks'
import { useNotificationsStore } from '@/stores/notifications'
import type { Task, TaskStatus } from '@/types'
import SpBadge from '@/components/ui/SpBadge.vue'
import SpSpinner from '@/components/ui/SpSpinner.vue'
import SpModal from '@/components/ui/SpModal.vue'
import SpSelect from '@/components/ui/SpSelect.vue'

const notifications = useNotificationsStore()
const allTasks = ref<Task[]>([])
const loading = ref(false)
const showModal = ref(false)
const activeTask = ref<Task | null>(null)
const editStatus = ref('')

const store = { loading }

const columns = [
  { key: 'pending',     label: 'Pending' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'blocked',     label: 'Blocked' },
  { key: 'done',        label: 'Done' },
]

const statusOptions = [
  { value: 'pending',     label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'blocked',     label: 'Blocked' },
  { value: 'done',        label: 'Done' },
]

const tasksInCol = (key: string) => allTasks.value.filter((t) => t.status === key)

function openTask(task: Task) {
  activeTask.value = task
  editStatus.value = task.status
  showModal.value = true
}

async function updateStatus(newStatus: string) {
  if (!activeTask.value) return
  try {
    const updated = await tasksApi.update(activeTask.value.id, { status: newStatus as TaskStatus })
    const idx = allTasks.value.findIndex((t) => t.id === activeTask.value!.id)
    if (idx !== -1) allTasks.value[idx] = updated
    notifications.show('Task status updated', 'success')
  } catch { /* ignore */ }
}

function prioCls(p: number) { return p === 1 ? 'high' : p === 2 ? 'medium' : 'low' }
function taskTypeIcon(type: string) {
  const icons: Record<string, string> = { setup: '🔧', teardown: '🔄', av_config: '📺', catering: '🍽', security: '🔒', cleaning: '🧹', coordination: '📋', other: '📌' }
  return icons[type] ?? '📌'
}
function formatDue(dt: string) {
  return new Date(dt).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' })
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await tasksApi.list({ limit: 200 } as any)
    allTasks.value = res.items ?? res
  } finally { loading.value = false }
})
</script>

<style scoped>
.kanban-board { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); align-items: start; }
.kanban-col   { background: var(--bg-secondary); border-radius: var(--radius-lg); overflow: hidden; }
.kanban-col__header {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--surface); border-bottom: 1px solid var(--border);
}
.kanban-col__title { font-weight: 600; font-size: var(--text-sm); }
.kanban-col__count {
  background: var(--bg-tertiary); color: var(--text-secondary);
  font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: var(--radius-full);
}
.kanban-col__body { padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-2); min-height: 120px; }
.kanban-empty { text-align: center; color: var(--text-tertiary); font-size: var(--text-sm); padding: var(--space-4); }

.task-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: var(--space-3);
  cursor: pointer; transition: box-shadow var(--transition-fast);
}
.task-card:hover { box-shadow: var(--shadow-sm); }
.task-card__header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); }
.task-prio { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.task-prio--high   { background: var(--error); }
.task-prio--medium { background: var(--warning); }
.task-prio--low    { background: var(--success); }
.task-type { font-size: var(--text-xs); color: var(--text-secondary); }
.task-card__title { font-size: var(--text-sm); font-weight: 500; margin-bottom: var(--space-2); }
.task-card__footer { display: flex; justify-content: space-between; align-items: center; }
.task-due { font-size: var(--text-xs); color: var(--text-tertiary); }

.task-detail { display: flex; flex-direction: column; gap: var(--space-3); }
.detail-row { display: flex; align-items: center; justify-content: space-between; font-size: var(--text-sm); padding: var(--space-2) 0; border-bottom: 1px solid var(--border-light); }
.detail-row span:first-child { color: var(--text-secondary); }
.detail-desc { font-size: var(--text-sm); color: var(--text-secondary); background: var(--bg-tertiary); padding: var(--space-3); border-radius: var(--radius-md); }
</style>
```

---

## Phase F9 — 3D Visualization Tab

### `frontend/src/components/visualization/ThreeDFrame.vue`

```vue
<template>
  <div class="three-d-container">
    <iframe
      ref="frame"
      :src="frameSrc"
      class="three-d-iframe"
      allow="fullscreen; accelerometer; gyroscope"
      @load="onLoad"
    />
    <div v-if="!loaded" class="three-d-loading">
      <SpSpinner :size="40" />
      <span>Loading 3D view…</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import SpSpinner from '@/components/ui/SpSpinner.vue'

const THREE_D_URL = import.meta.env.VITE_THREE_D_URL ?? 'http://localhost:3000'

const props = defineProps<{ roomId?: string }>()
const emit = defineEmits<{ layoutSaved: [data: any] }>()

const frame = ref<HTMLIFrameElement>()
const loaded = ref(false)

const frameSrc = computed(() =>
  props.roomId ? `${THREE_D_URL}?autoRoom=${props.roomId}` : THREE_D_URL,
)

function onLoad() { loaded.value = true }

function handleMessage(event: MessageEvent) {
  if (event.origin !== THREE_D_URL) return
  if (event.data?.type === 'LAYOUT_SAVED') {
    emit('layoutSaved', event.data)
  }
}

function sendCommand(type: string, payload: object) {
  frame.value?.contentWindow?.postMessage({ type, payload }, THREE_D_URL)
}

onMounted(() => window.addEventListener('message', handleMessage))
onUnmounted(() => window.removeEventListener('message', handleMessage))

defineExpose({ sendCommand })
</script>

<style scoped>
.three-d-container { position: relative; width: 100%; height: calc(100vh - 160px); min-height: 500px; border-radius: var(--radius-lg); overflow: hidden; }
.three-d-iframe { width: 100%; height: 100%; border: none; }
.three-d-loading {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-3); background: var(--bg-secondary); color: var(--text-secondary);
}
</style>
```

---

### `frontend/src/views/admin/VisualizationView.vue`

```vue
<template>
  <div class="viz-view">
    <div class="viz-toolbar">
      <SpSelect
        v-model="selectedVenueId"
        :options="venueOptions"
        placeholder="Navigate to room..."
        style="width: 220px;"
        @update:modelValue="navigateToRoom"
      />
      <SpButton variant="primary" @click="openAiDesigner">✦ AI Design Room</SpButton>
      <a :href="THREE_D_URL" target="_blank" class="fullscreen-link">Open Fullscreen ↗</a>
    </div>
    <ThreeDFrame ref="frameRef" :room-id="selectedRoomId" @layout-saved="onLayoutSaved" />
    <AiChatPanel v-model="showAiPanel" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { venuesApi } from '@/api/venues'
import { useAiStore } from '@/stores/ai'
import { useNotificationsStore } from '@/stores/notifications'
import type { Venue } from '@/types'
import SpButton from '@/components/ui/SpButton.vue'
import SpSelect from '@/components/ui/SpSelect.vue'
import ThreeDFrame from '@/components/visualization/ThreeDFrame.vue'
import AiChatPanel from '@/components/ai/AiChatPanel.vue'

const THREE_D_URL = import.meta.env.VITE_THREE_D_URL ?? 'http://localhost:3000'
const aiStore = useAiStore()
const notifications = useNotificationsStore()

const venues = ref<Venue[]>([])
const selectedVenueId = ref('')
const frameRef = ref<InstanceType<typeof ThreeDFrame>>()
const showAiPanel = ref(false)

const selectedVenue = computed(() => venues.value.find((v) => v.id === selectedVenueId.value))
const selectedRoomId = computed(() => selectedVenue.value?.three_d_room_id ?? undefined)
const venueOptions = computed(() => venues.value.map((v) => ({ value: v.id, label: v.name })))

function navigateToRoom(venueId: string) {
  const venue = venues.value.find((v) => v.id === venueId)
  if (venue?.three_d_room_id) {
    frameRef.value?.sendCommand('NAVIGATE_TO_ROOM', { roomId: venue.three_d_room_id })
  }
}

function openAiDesigner() {
  const venue = selectedVenue.value
  aiStore.setContext('room_designer', {
    venue_name: venue?.name ?? '',
    event_request_id: null,
  })
  showAiPanel.value = true
}

function onLayoutSaved(data: any) {
  notifications.show('Layout saved from 3D view', 'success')
}

onMounted(async () => {
  try { venues.value = (await venuesApi.list()).items } catch { /* ignore */ }
})
</script>

<style scoped>
.viz-view        { display: flex; flex-direction: column; gap: var(--space-4); height: 100%; }
.viz-toolbar     { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.fullscreen-link { font-size: var(--text-sm); color: var(--accent); font-weight: 500; text-decoration: none; }
.fullscreen-link:hover { text-decoration: underline; }
</style>
```

---

## Phase F10 — AI Copilot Chat Panel

### `frontend/src/components/ai/AiTypingIndicator.vue`

```vue
<template>
  <div class="ai-typing">
    <span v-for="i in 3" :key="i" class="ai-dot" :style="{ animationDelay: (i - 1) * 0.2 + 's' }" />
  </div>
</template>

<style scoped>
.ai-typing { display: flex; gap: 4px; align-items: center; padding: var(--space-2) 0; }
.ai-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent); opacity: 0.7;
  animation: bounce 1.1s ease-in-out infinite;
}
@keyframes bounce { 0%, 80%, 100% { transform: scale(0.8); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
</style>
```

---

### `frontend/src/components/ai/AiMessage.vue`

```vue
<template>
  <div :class="['ai-msg', `ai-msg--${message.role}`]">
    <div v-if="message.role === 'assistant'" class="ai-msg__avatar">✦</div>
    <div class="ai-msg__bubble">
      <div class="ai-msg__content" v-html="renderMarkdown(message.content)" />
      <div v-if="message.tool_calls?.length" class="ai-msg__tools">
        <span class="ai-tools-label">Tools used:</span>
        <span
          v-for="tc in message.tool_calls"
          :key="tc.tool"
          class="ai-tool-chip"
        >{{ tc.tool }}</span>
      </div>
      <span class="ai-msg__time">{{ formatTime(message.timestamp) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AiMessage } from '@/types'
defineProps<{ message: AiMessage }>()

function renderMarkdown(text: string) {
  // Simple markdown renderer (bold, italic, code, line breaks)
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}
function formatTime(d: Date) {
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.ai-msg { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); }
.ai-msg--user { flex-direction: row-reverse; }
.ai-msg__avatar {
  width: 30px; height: 30px; border-radius: var(--radius-full);
  background: var(--accent); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem; flex-shrink: 0; margin-top: 2px;
}
.ai-msg__bubble { max-width: 80%; }
.ai-msg--user .ai-msg__bubble { align-items: flex-end; display: flex; flex-direction: column; }
.ai-msg__content {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg); font-size: var(--text-sm); line-height: 1.65;
}
.ai-msg--assistant .ai-msg__content { background: var(--surface); border: 1px solid var(--border); border-radius: 0 var(--radius-lg) var(--radius-lg); }
.ai-msg--user .ai-msg__content      { background: var(--accent); color: #fff; border-radius: var(--radius-lg) 0 var(--radius-lg) var(--radius-lg); }
.ai-msg__tools { display: flex; flex-wrap: wrap; gap: var(--space-1); margin-top: var(--space-2); align-items: center; }
.ai-tools-label { font-size: var(--text-xs); color: var(--text-tertiary); }
.ai-tool-chip {
  font-size: var(--text-xs); background: var(--accent-light); color: var(--accent-dark);
  padding: 1px 6px; border-radius: var(--radius-full); font-weight: 500;
}
.ai-msg__time { font-size: 11px; color: var(--text-tertiary); margin-top: var(--space-1); display: block; }
</style>
```

---

### `frontend/src/components/ai/AiChatPanel.vue`

```vue
<template>
  <Teleport to="body">
    <Transition name="panel">
      <div v-if="modelValue" class="ai-panel">
        <!-- Header -->
        <div class="ai-panel__header">
          <div class="ai-panel__title">
            <span class="ai-panel__icon">✦</span>
            <span>AI Copilot</span>
            <SpBadge :variant="agentBadgeVariant" style="margin-left: var(--space-2);">
              {{ agentStore.agentType }}
            </SpBadge>
          </div>
          <div class="ai-panel__header-right">
            <button class="ai-panel__clear" title="Clear chat" @click="aiStore.clearMessages">🗑</button>
            <button class="ai-panel__close" @click="$emit('update:modelValue', false)">✕</button>
          </div>
        </div>

        <!-- Messages -->
        <div class="ai-panel__messages" ref="messagesEl">
          <div v-if="aiStore.messages.length === 0" class="ai-panel__empty">
            <p class="ai-panel__empty-title">Hello! I'm your SpaceFlow AI Copilot.</p>
            <p class="ai-panel__empty-sub">Ask me about venues, inventory, conflicts, or room design.</p>
            <!-- Quick chips -->
            <div class="ai-chips">
              <button
                v-for="chip in quickChips"
                :key="chip"
                class="ai-chip"
                @click="sendChip(chip)"
              >{{ chip }}</button>
            </div>
          </div>
          <AiMessage
            v-for="(msg, i) in aiStore.messages"
            :key="i"
            :message="msg"
          />
          <div v-if="aiStore.isLoading" class="ai-msg ai-msg--assistant">
            <div class="ai-msg__avatar">✦</div>
            <div class="ai-msg__bubble">
              <div class="ai-msg__content" style="background: var(--surface); border: 1px solid var(--border); border-radius: 0 var(--radius-lg) var(--radius-lg);">
                <AiTypingIndicator />
              </div>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div class="ai-panel__input-area">
          <div class="ai-panel__input-row">
            <textarea
              ref="textareaEl"
              v-model="inputText"
              class="ai-panel__textarea"
              placeholder="Ask anything about events, venues, or rooms…"
              rows="1"
              @keydown.enter.exact.prevent="send"
              @input="autoResize"
            />
            <button
              class="ai-panel__send"
              :disabled="!inputText.trim() || aiStore.isLoading"
              @click="send"
            >↑</button>
          </div>
          <p class="ai-panel__hint">Press Enter to send · Shift+Enter for new line</p>
        </div>
      </div>
    </Transition>
    <!-- Backdrop -->
    <Transition name="backdrop">
      <div v-if="modelValue" class="ai-panel-backdrop" @click="$emit('update:modelValue', false)" />
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useAiStore } from '@/stores/ai'
import SpBadge from '@/components/ui/SpBadge.vue'
import AiMessage from './AiMessage.vue'
import AiTypingIndicator from './AiTypingIndicator.vue'

defineProps<{ modelValue: boolean }>()
defineEmits(['update:modelValue'])

const aiStore = useAiStore()
const agentStore = aiStore  // same store
const inputText = ref('')
const messagesEl = ref<HTMLElement>()
const textareaEl = ref<HTMLTextAreaElement>()

const agentBadgeVariant = computed(() => {
  const map: Record<string, string> = {
    copilot: 'info', room_designer: 'accent',
    intake: 'success', conflict_detector: 'warning', planner: 'neutral',
  }
  return (map[aiStore.agentType] as any) ?? 'info'
})

const quickChips = computed(() => {
  if (aiStore.agentType === 'room_designer') {
    return ['Design for 40-person workshop', 'Set up hackathon layout', 'Conference theater seating']
  }
  return [
    'List available venues today',
    'Check my latest request status',
    'What assets are running low?',
    'Generate operational tasks',
  ]
})

async function send() {
  const text = inputText.value.trim()
  if (!text || aiStore.isLoading) return
  inputText.value = ''
  resetTextarea()
  await aiStore.sendMessage(text)
  scrollToBottom()
}

function sendChip(chip: string) {
  inputText.value = chip
  send()
}

function autoResize() {
  const el = textareaEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function resetTextarea() {
  if (textareaEl.value) textareaEl.value.style.height = 'auto'
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

watch(() => aiStore.messages.length, scrollToBottom)
</script>

<style scoped>
.ai-panel {
  position: fixed; right: 0; top: 0; bottom: 0;
  width: 420px; z-index: var(--z-ai-panel);
  background: var(--bg-secondary);
  border-left: 1px solid var(--border);
  box-shadow: -4px 0 24px rgba(18,38,58,0.12);
  display: flex; flex-direction: column;
}
.ai-panel-backdrop {
  position: fixed; inset: 0; z-index: calc(var(--z-ai-panel) - 1);
  background: transparent;
}

.ai-panel__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  background: var(--surface); border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.ai-panel__title { display: flex; align-items: center; gap: var(--space-2); font-weight: 700; font-size: var(--text-base); }
.ai-panel__icon  { color: var(--accent); font-size: 1.1rem; }
.ai-panel__header-right { display: flex; align-items: center; gap: var(--space-2); }
.ai-panel__clear, .ai-panel__close {
  width: 30px; height: 30px; border: none; background: transparent;
  color: var(--text-tertiary); cursor: pointer; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-sm); transition: background var(--transition-fast);
}
.ai-panel__clear:hover, .ai-panel__close:hover { background: var(--bg-tertiary); color: var(--text-primary); }

.ai-panel__messages {
  flex: 1; overflow-y: auto; padding: var(--space-4) var(--space-5);
  scroll-behavior: smooth;
}

.ai-panel__empty { text-align: center; padding: var(--space-6) 0; }
.ai-panel__empty-title { font-weight: 600; margin-bottom: var(--space-2); }
.ai-panel__empty-sub   { font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-5); }
.ai-chips { display: flex; flex-direction: column; gap: var(--space-2); }
.ai-chip  {
  padding: var(--space-3) var(--space-4); font-size: var(--text-sm);
  text-align: left; background: var(--surface); border: 1.5px solid var(--border);
  border-radius: var(--radius-lg); cursor: pointer; color: var(--text-primary);
  transition: all var(--transition-fast);
}
.ai-chip:hover { border-color: var(--accent); background: var(--accent-light); color: var(--accent-dark); }

.ai-panel__input-area { flex-shrink: 0; padding: var(--space-4) var(--space-5); border-top: 1px solid var(--border); background: var(--surface); }
.ai-panel__input-row  { display: flex; gap: var(--space-2); align-items: flex-end; }
.ai-panel__textarea {
  flex: 1; padding: var(--space-3);
  background: var(--bg-tertiary); border: 1.5px solid var(--border);
  border-radius: var(--radius-lg); font-family: var(--font-sans); font-size: var(--text-sm);
  color: var(--text-primary); resize: none; outline: none; overflow: hidden;
  transition: border-color var(--transition-fast); min-height: 42px; max-height: 120px;
}
.ai-panel__textarea:focus { border-color: var(--accent); background: var(--surface); }
.ai-panel__send {
  width: 38px; height: 38px; border-radius: var(--radius-md);
  background: var(--accent); color: #fff; border: none;
  cursor: pointer; font-size: 1.1rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  transition: background var(--transition-fast); flex-shrink: 0;
}
.ai-panel__send:hover:not(:disabled) { background: var(--accent-hover); }
.ai-panel__send:disabled { opacity: 0.5; cursor: not-allowed; }
.ai-panel__hint { font-size: 11px; color: var(--text-tertiary); margin-top: var(--space-2); }

/* Transitions */
.panel-enter-active  { transition: transform 0.25s ease, opacity 0.25s ease; }
.panel-leave-active  { transition: transform 0.2s ease, opacity 0.2s ease; }
.panel-enter-from, .panel-leave-to { transform: translateX(100%); opacity: 0; }
.backdrop-enter-active, .backdrop-leave-active { transition: opacity 0.2s; }
.backdrop-enter-from, .backdrop-leave-to { opacity: 0; }
</style>
```

---

## Phase F4 — Admin Dashboard

### `frontend/src/views/admin/DashboardView.vue`

```vue
<template>
  <div class="dashboard">
    <!-- KPI widgets -->
    <div class="kpi-grid">
      <SpCard v-for="kpi in kpis" :key="kpi.label" class="kpi-card">
        <div class="kpi-icon">{{ kpi.icon }}</div>
        <div class="kpi-body">
          <div class="kpi-value">{{ kpi.value }}</div>
          <div class="kpi-label">{{ kpi.label }}</div>
        </div>
      </SpCard>
    </div>

    <div class="dashboard-grid">
      <!-- Recent Requests -->
      <div class="dashboard-section">
        <div class="section-header">
          <h3>Recent Requests</h3>
          <RouterLink to="/admin/requests" class="section-link">View all →</RouterLink>
        </div>
        <div v-if="requestsStore.loading"><SpSpinner :size="28" /></div>
        <div v-else class="recent-requests">
          <RequestCard
            v-for="req in recentRequests"
            :key="req.id"
            :request="req"
          />
          <div v-if="recentRequests.length === 0" class="empty-state">No requests yet.</div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="dashboard-section">
        <h3 class="section-header">Quick Actions</h3>
        <div class="quick-actions">
          <RouterLink to="/book">
            <SpButton variant="secondary" class="w-full quick-action-btn">+ Submit New Request</SpButton>
          </RouterLink>
          <RouterLink to="/admin/inventory">
            <SpButton variant="secondary" class="w-full quick-action-btn">📦 View Inventory</SpButton>
          </RouterLink>
          <RouterLink to="/admin/calendar">
            <SpButton variant="secondary" class="w-full quick-action-btn">📅 Open Calendar</SpButton>
          </RouterLink>
          <RouterLink to="/admin/visualization">
            <SpButton variant="secondary" class="w-full quick-action-btn">🏛 3D View</SpButton>
          </RouterLink>
          <SpButton variant="primary" class="w-full quick-action-btn" @click="openAi">
            ✦ AI Copilot
          </SpButton>
        </div>

        <!-- Live connection status -->
        <div class="live-status">
          <div class="live-indicator" :class="wsStore.connected ? 'live-indicator--on' : 'live-indicator--off'" />
          <span>{{ wsStore.connected ? 'Live updates active' : 'Connecting to live feed…' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRequestsStore } from '@/stores/requests'
import { useAssetsStore } from '@/stores/assets'
import { useWebSocketStore } from '@/stores/websocket'
import { useAiStore } from '@/stores/ai'
import SpCard from '@/components/ui/SpCard.vue'
import SpButton from '@/components/ui/SpButton.vue'
import SpSpinner from '@/components/ui/SpSpinner.vue'
import RequestCard from '@/components/requests/RequestCard.vue'

const requestsStore = useRequestsStore()
const assetsStore = useAssetsStore()
const wsStore = useWebSocketStore()
const aiStore = useAiStore()

const recentRequests = computed(() => requestsStore.items.slice(0, 5))

const kpis = computed(() => [
  { icon: '📋', label: 'Total Requests',    value: requestsStore.total },
  { icon: '✓',  label: 'Approved',          value: requestsStore.items.filter((r) => r.status === 'approved').length },
  { icon: '⏳', label: 'Under Review',       value: requestsStore.items.filter((r) => r.status === 'under_review' || r.status === 'submitted').length },
  { icon: '📦', label: 'Asset Types',        value: assetsStore.items.length },
])

function openAi() {
  aiStore.setContext('copilot', {})
  // The global panel is controlled by AdminLayout.vue — emit via a flag on window
  ;(window as any).__openAiPanel?.()
}

onMounted(async () => {
  await requestsStore.fetchList({ limit: 20 })
  await assetsStore.fetchAll()
})
</script>

<style scoped>
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); margin-bottom: var(--space-6); }
.kpi-card { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-5); }
.kpi-icon  { font-size: 2rem; flex-shrink: 0; }
.kpi-value { font-size: var(--text-3xl); font-weight: 700; color: var(--text-primary); }
.kpi-label { font-size: var(--text-sm); color: var(--text-secondary); }

.dashboard-grid { display: grid; grid-template-columns: 1fr 320px; gap: var(--space-6); }
.dashboard-section { }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }
.section-header h3 { font-size: var(--text-lg); font-weight: 600; }
.section-link { font-size: var(--text-sm); color: var(--accent); }
.recent-requests { display: flex; flex-direction: column; gap: var(--space-3); }
.empty-state { text-align: center; padding: var(--space-8); color: var(--text-tertiary); font-size: var(--text-sm); }

.quick-actions { display: flex; flex-direction: column; gap: var(--space-2); }
.quick-action-btn { justify-content: flex-start; text-align: left; }

.live-status {
  display: flex; align-items: center; gap: var(--space-2);
  margin-top: var(--space-4); padding: var(--space-3);
  background: var(--bg-tertiary); border-radius: var(--radius-md);
  font-size: var(--text-xs); color: var(--text-secondary);
}
.live-indicator { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.live-indicator--on  { background: var(--success); animation: pulse 1.5s infinite; }
.live-indicator--off { background: var(--warning); }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
```

---

## 12. Admin WebSocket Integration

The `stores/websocket.ts` (written in Phase F1) connects to `ws://localhost:8080/ws/admin` on login and handles three message types:

| Backend Event | Frontend Action |
|---|---|
| `REQUEST_SUBMITTED` | Toast + refresh request list |
| `REQUEST_STATUS_CHANGED` | Toast + re-fetch active request if open |
| `LAYOUT_AI_APPLIED` | Toast confirming 3D layout was pushed |

The `AdminLayout.vue` starts the WS on mount; the connection is reused across all admin views via the Pinia singleton.

---

## 13. Vite Config, tsconfig & package.json

### `frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8080', changeOrigin: true },
      '/ws':  { target: 'ws://localhost:8080',   ws: true, changeOrigin: true },
    },
  },
})
```

### `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### `frontend/tsconfig.node.json`

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

### `frontend/package.json`

```json
{
  "name": "spaceflow-frontend",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev":     "vite",
    "build":   "vue-tsc && vite build",
    "preview": "vite preview",
    "type-check": "vue-tsc --noEmit"
  },
  "dependencies": {
    "vue":                   "^3.4.0",
    "vue-router":            "^4.3.0",
    "pinia":                 "^2.1.0",
    "axios":                 "^1.6.0",
    "@vueuse/core":          "^10.9.0",
    "@fullcalendar/core":    "^6.1.0",
    "@fullcalendar/vue3":    "^6.1.0",
    "@fullcalendar/daygrid": "^6.1.0",
    "@fullcalendar/timegrid":"^6.1.0",
    "@fullcalendar/interaction": "^6.1.0",
    "chart.js":              "^4.4.0",
    "vue-chartjs":           "^5.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue":    "^5.0.0",
    "typescript":            "^5.3.0",
    "vite":                  "^5.1.0",
    "vue-tsc":               "^2.0.0"
  }
}
```

### `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SpaceFlow — Pyramid of Tirana</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⬡</text></svg>" />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

---

## Implementation Order

The phases must be implemented in this sequence to avoid broken imports:

| Phase | Files | Dependency |
|-------|-------|------------|
| F1-a | `package.json`, `vite.config.ts`, `tsconfig.json`, `.env` | Bootstrap |
| F1-b | `types/index.ts` | None |
| F1-c | `assets/styles/` (tokens, base, utilities) | None |
| F1-d | `api/` (client + all API modules) | types |
| F1-e | `stores/` (auth, requests, assets, notifications, websocket, ai) | api + types |
| F1-f | `router/index.ts` | stores |
| F1-g | `main.ts`, `App.vue` | router + stores |
| F1-h | `components/ui/` (SpButton, SpBadge, SpCard, SpInput, SpSelect, SpModal, SpToast, SpSpinner) | tokens |
| F1-i | `components/layout/` (AppNav, AdminSidebar, AdminLayout) | ui + stores |
| F2   | `views/public/` (HomeView, VenuesView, BookingView) | api + ui + AppNav |
| F3   | `views/auth/` (LoginView, RegisterView) | stores.auth + ui |
| F4   | `components/requests/` + `views/admin/RequestsView` + `RequestDetailView` | ui + stores |
| F5   | `components/inventory/` + `views/admin/InventoryView` | stores.assets |
| F6   | `views/admin/CalendarView` | FullCalendar + api |
| F7   | `views/admin/QuotationsView` | stores.requests |
| F8   | `views/admin/TasksView` + `components/tasks/TaskCard` | api.tasks |
| F9   | `components/visualization/ThreeDFrame` + `views/admin/VisualizationView` | api.venues |
| F10  | `components/ai/` + `stores/ai` + wired into AdminLayout | api.ai + stores.ai |

---

*FRONTEND_BLUEPRINT.md — SpaceFlow · JunctionX Tirana 2026*
*Vue 3 + Vite + TypeScript | Port 5173 | Connects to backend on 8080 · 3D app on 3000*
