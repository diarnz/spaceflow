export type UserRole = 'admin' | 'staff' | 'client'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  phone: string | null
  organization: string | null
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string | null
  token_type: string
  expires_in: number | null
  user: User | null
  requires_email_verification: boolean
  message: string | null
}

export type TokenResponse = AuthResponse

export type VenueStatus = 'active' | 'maintenance' | 'unavailable'

export interface Venue {
  id: string
  name: string
  floor: number
  capacity_min: number
  capacity_max: number
  area_sqm: string | null
  description: string | null
  amenities: string[]
  status: VenueStatus
  three_d_room_id: string | null
  color_hex: string | null
  base_price_per_hour: string
  created_at: string
}

export interface AvailableSlot {
  start: string
  end: string
}

export interface OccupiedSlot {
  start: string
  end: string
  event_request_id: string
  event_title: string
  attendees: number
}

export interface VenueAvailabilityResponse {
  venue_id: string
  date: string
  duration_hours: number
  available_slots: AvailableSlot[]
  occupied_slots: OccupiedSlot[]
  is_fully_available: boolean
}

export type EventStatus =
  | 'draft'
  | 'submitted'
  | 'under_review'
  | 'quotation_sent'
  | 'approved'
  | 'confirmed'
  | 'rejected'
  | 'cancelled'
  | 'completed'

export type EventType =
  | 'conference'
  | 'workshop'
  | 'concert'
  | 'exhibition'
  | 'hackathon'
  | 'dinner'
  | 'private'
  | 'other'

export interface EventRequestCreatePayload {
  title: string
  event_type: EventType
  description?: string
  requested_date: string
  start_time: string
  end_time: string
  attendee_count: number
  venue_id?: string
  special_requirements?: string
  setup_time_minutes?: number
  teardown_time_minutes?: number
}

export interface EventRequestSummary {
  id: string
  title: string
  event_type: string
  status: EventStatus
  requested_date: string
  start_time: string
  end_time: string
  attendee_count: number
  venue_id: string | null
  venue_name: string | null
  client_id: string | null
  client_name: string | null
  has_ai_proposal: boolean
  has_conflicts: boolean
  created_at: string
}

export interface EventRequestDetail {
  id: string
  title: string
  event_type: string
  description: string | null
  status: EventStatus
  requested_date: string
  start_time: string
  end_time: string
  attendee_count: number
  setup_time_minutes: number
  teardown_time_minutes: number
  special_requirements: string | null
  venue_id: string | null
  venue: Venue | null
  client_id: string | null
  client: User | null
  assigned_staff_id: string | null
  rejection_reason: string | null
  ai_proposal_json: AiProposal | null
  created_at: string
  updated_at: string
}

export interface StatusTransitionResponse {
  id: string
  previous_status: string
  new_status: string
  message: string
}

export type ConflictSeverity = 'blocking' | 'warning'

export interface Conflict {
  type?: string
  severity: ConflictSeverity
  description: string
  suggestion: string
  affected_resource?: string
}

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
  category: AssetCategory | string
  tracking_type: 'pool' | 'instance'
  total_quantity: number
  description: string | null
  unit_price: string
  three_d_item_key: string | null
  is_active: boolean
  created_at: string
}

export interface AssetAvailabilityResponse {
  asset_id: string
  asset_name: string
  total_quantity: number
  reserved_quantity: number
  available_quantity: number
  is_available: boolean
  reservations_in_window: Record<string, unknown>[]
}

export interface AssetSummaryItem {
  asset_id: string
  name: string
  category: string
  total_quantity: number
  available_quantity: number
  reserved_quantity: number
  availability_pct: number
  has_conflict_next_7_days: boolean
}

export interface ReservationResponse {
  id: string
  event_request_id: string
  asset_id: string
  asset_name: string
  quantity_requested: number
  quantity_confirmed: number
  reservation_start: string
  reservation_end: string
  status: 'pending' | 'confirmed' | 'cancelled' | 'released'
  notes: string | null
  created_at: string
}

export interface BulkReserveResult {
  asset_id: string
  name: string
  requested: number
  confirmed: number
  status: string
  shortfall?: number | null
  conflict_reason?: string | null
}

export interface BulkReserveResponse {
  can_fulfill_all: boolean
  results: BulkReserveResult[]
}

export interface QuotationLineItem {
  category: string
  name: string
  qty: number
  unit_price: string
  total: string
}

export interface QuotationResponse {
  id: string
  event_request_id: string
  line_items: QuotationLineItem[]
  subtotal: string
  tax_rate: string
  tax_amount: string
  total_amount: string
  valid_until: string
  status: 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired'
  generated_by_ai: boolean
  ai_notes: string | null
  admin_notes: string | null
  sent_at: string | null
  accepted_at: string | null
  created_at: string
}

export type TaskType = 'setup' | 'teardown' | 'preparation' | 'logistics' | 'coordination'
export type TaskStatus = 'pending' | 'assigned' | 'in_progress' | 'done' | 'blocked'

export interface TaskResponse {
  id: string
  event_request_id: string
  event_title: string | null
  title: string
  description: string | null
  task_type: TaskType
  assigned_to: string | null
  assignee_name: string | null
  due_at: string
  completed_at: string | null
  status: TaskStatus
  priority: number
  depends_on: string | null
  ai_generated: boolean
  created_at: string
}

export interface RoomLayoutItem {
  modelKey: string
  x: number
  y: number
  z: number
  rotY: number
  type: 'floor' | 'wall'
  surfaceY?: number | null
  wallAxis?: 'x' | 'z' | null
  wallCoord?: number | null
  isPositiveWall?: boolean | null
  mountY?: number | null
  scale?: Record<string, number> | null
  stackOn?: number | null
  lxf?: number | null
  lzf?: number | null
  lx?: number | null
  lz?: number | null
}

export interface RoomLayoutResponse {
  id: string
  venue_id: string
  venue_name: string | null
  three_d_room_id: string | null
  event_request_id: string | null
  name: string
  items_json: RoomLayoutItem[]
  item_count: number
  source: 'manual' | 'template' | 'ai_generated'
  ai_prompt: string | null
  thumbnail_url: string | null
  is_current: boolean
  created_at: string
}

export type AgentType = 'copilot' | 'room_designer' | 'intake' | 'conflict_detector' | 'planner'

export interface AIChatResponse {
  response: string
  tool_calls_made: ToolCall[]
  conversation_id: string
}

export interface AIAgentResponse {
  response: string
  agent_type: string
  tool_calls_made: ToolCall[]
  conversation_id: string | null
  iterations: number
}

export interface AIConversationSummary {
  id: string
  agent_type: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface AIConversationDetail {
  id: string
  agent_type: string
  messages: Record<string, unknown>[]
  context_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AIToolInfo {
  name: string
  description: string
  agent_types: string[]
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
  result: Record<string, unknown>
}

export interface AiMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  toolCalls?: ToolCall[]
}

export interface AiProposal {
  status?: string
  summary?: string
  tool_calls?: ToolCall[]
  recommended_venue?: {
    id: string | null
    name: string | null
    reason: string
  }
  availability?: {
    is_fully_available: boolean
    available_slots: AvailableSlot[]
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
    breakdown: {
      category: string
      name: string
      total: number
    }[]
  }
  conflicts?: Conflict[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface WsMessage<T = Record<string, unknown>> {
  type: string
  payload: T
}
