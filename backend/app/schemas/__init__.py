from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class MessageResponse(BaseModel):
    message: str


class IDResponse(BaseModel):
    id: UUID


class UserResponse(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: Literal["admin", "staff", "client"]
    phone: str | None = None
    organization: str | None = None
    is_active: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    organization: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)
    phone: str | None = None
    organization: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthExchangeRequest(BaseModel):
    access_token: str = Field(min_length=1)


class AuthResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    user: UserResponse | None = None
    requires_email_verification: bool = False
    message: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class VenueResponse(ORMModel):
    id: UUID
    name: str
    floor: int
    capacity_min: int
    capacity_max: int
    area_sqm: Decimal | None = None
    description: str | None = None
    amenities: list[str]
    status: Literal["active", "maintenance", "unavailable"]
    three_d_room_id: str | None = None
    color_hex: str | None = None
    base_price_per_hour: Decimal
    created_at: datetime


class VenueCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    floor: int = Field(ge=-5, le=20)
    capacity_min: int = Field(default=0, ge=0)
    capacity_max: int = Field(gt=0)
    area_sqm: Decimal | None = None
    description: str | None = None
    amenities: list[str] = Field(default_factory=list)
    three_d_room_id: str | None = None
    color_hex: str | None = None
    base_price_per_hour: Decimal = Field(default=Decimal("0"), ge=0)


class VenueUpdateRequest(BaseModel):
    name: str | None = None
    floor: int | None = None
    capacity_min: int | None = None
    capacity_max: int | None = None
    area_sqm: Decimal | None = None
    description: str | None = None
    amenities: list[str] | None = None
    status: Literal["active", "maintenance", "unavailable"] | None = None
    three_d_room_id: str | None = None
    color_hex: str | None = None
    base_price_per_hour: Decimal | None = None


class AvailableSlot(BaseModel):
    start: str
    end: str


class OccupiedSlot(BaseModel):
    start: str
    end: str
    event_request_id: UUID
    event_title: str
    attendees: int


class VenueAvailabilityResponse(BaseModel):
    venue_id: UUID
    date: date
    duration_hours: float
    available_slots: list[AvailableSlot]
    occupied_slots: list[OccupiedSlot]
    is_fully_available: bool


EventStatus = Literal[
    "draft",
    "submitted",
    "under_review",
    "quotation_sent",
    "approved",
    "confirmed",
    "rejected",
    "cancelled",
    "completed",
]
EventType = Literal[
    "conference",
    "workshop",
    "concert",
    "exhibition",
    "hackathon",
    "dinner",
    "private",
    "other",
]


class EventRequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    event_type: EventType
    description: str | None = None
    requested_date: date
    start_time: time
    end_time: time
    attendee_count: int = Field(gt=0, le=10000)
    venue_id: UUID | None = None
    special_requirements: str | None = None
    setup_time_minutes: int = Field(default=60, ge=0, le=480)
    teardown_time_minutes: int = Field(default=60, ge=0, le=480)

    @model_validator(mode="after")
    def validate_times(self) -> "EventRequestCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class EventRequestUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    requested_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    attendee_count: int | None = Field(default=None, gt=0, le=10000)
    venue_id: UUID | None = None
    special_requirements: str | None = None
    setup_time_minutes: int | None = Field(default=None, ge=0, le=480)
    teardown_time_minutes: int | None = Field(default=None, ge=0, le=480)


class AssignVenueRequest(BaseModel):
    venue_id: UUID


class RejectRequest(BaseModel):
    reason: str = Field(min_length=5)


class EventRequestSummary(BaseModel):
    id: UUID
    title: str
    event_type: str
    status: EventStatus
    requested_date: date
    start_time: time
    end_time: time
    attendee_count: int
    venue_id: UUID | None = None
    venue_name: str | None = None
    client_id: UUID | None = None
    client_name: str | None = None
    has_ai_proposal: bool
    has_conflicts: bool
    created_at: datetime


class EventRequestDetail(BaseModel):
    id: UUID
    title: str
    event_type: str
    description: str | None = None
    status: EventStatus
    requested_date: date
    start_time: time
    end_time: time
    attendee_count: int
    setup_time_minutes: int
    teardown_time_minutes: int
    special_requirements: str | None = None
    venue_id: UUID | None = None
    venue: VenueResponse | None = None
    client_id: UUID | None = None
    client: UserResponse | None = None
    assigned_staff_id: UUID | None = None
    rejection_reason: str | None = None
    ai_proposal_json: Any | None = None
    created_at: datetime
    updated_at: datetime


class StatusTransitionResponse(BaseModel):
    id: UUID
    previous_status: EventStatus | str
    new_status: EventStatus | str
    message: str


AssetCategory = Literal["seating", "tables", "av_equipment", "staging", "lighting", "misc"]
ThreeDItemKey = Literal[
    "office_table",
    "office_chair",
    "office_monitor",
    "keyboard_mouse",
    "simple_table",
    "simple_chair",
    "speaker",
    "microphone_stand",
    "wall_flat_tv",
    "led_tv",
    "whiteboard",
]


class AssetResponse(ORMModel):
    id: UUID
    name: str
    category: AssetCategory | str
    tracking_type: Literal["pool", "instance"]
    total_quantity: int
    description: str | None = None
    unit_price: Decimal
    three_d_item_key: ThreeDItemKey | None = None
    is_active: bool
    created_at: datetime


class AssetCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    category: AssetCategory
    tracking_type: Literal["pool", "instance"] = "pool"
    total_quantity: int = Field(ge=0)
    description: str | None = None
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    three_d_item_key: ThreeDItemKey | None = None


class AssetAvailabilityResponse(BaseModel):
    asset_id: UUID
    asset_name: str
    total_quantity: int
    reserved_quantity: int
    available_quantity: int
    is_available: bool
    reservations_in_window: list[dict[str, Any]]


class AssetSummaryItem(BaseModel):
    asset_id: UUID
    name: str
    category: str
    total_quantity: int
    available_quantity: int
    reserved_quantity: int
    availability_pct: float
    has_conflict_next_7_days: bool


class BulkReserveItem(BaseModel):
    asset_id: UUID
    quantity: int = Field(gt=0)


class BulkReserveRequest(BaseModel):
    assets: list[BulkReserveItem]


class BulkReserveResult(BaseModel):
    asset_id: UUID
    name: str
    requested: int
    confirmed: int
    status: str
    shortfall: int | None = None
    conflict_reason: str | None = None


class BulkReserveResponse(BaseModel):
    can_fulfill_all: bool
    results: list[BulkReserveResult]


class ReservationCreate(BaseModel):
    event_request_id: UUID
    asset_id: UUID
    quantity_requested: int = Field(gt=0)
    reservation_start: datetime
    reservation_end: datetime


class ReservationResponse(BaseModel):
    id: UUID
    event_request_id: UUID
    asset_id: UUID
    asset_name: str
    quantity_requested: int
    quantity_confirmed: int
    reservation_start: datetime
    reservation_end: datetime
    status: Literal["pending", "confirmed", "cancelled", "released"]
    notes: str | None = None
    created_at: datetime


class QuotationLineItem(BaseModel):
    category: str
    name: str
    qty: int
    unit_price: Decimal
    total: Decimal


class QuotationResponse(BaseModel):
    id: UUID
    event_request_id: UUID
    line_items: list[QuotationLineItem]
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    valid_until: date
    status: Literal["draft", "sent", "accepted", "rejected", "expired"]
    generated_by_ai: bool
    ai_notes: str | None = None
    admin_notes: str | None = None
    sent_at: datetime | None = None
    accepted_at: datetime | None = None
    created_at: datetime


class QuotationUpdateRequest(BaseModel):
    line_items: list[QuotationLineItem] | None = None
    admin_notes: str | None = None
    tax_rate: Decimal | None = None


TaskType = Literal["setup", "teardown", "preparation", "logistics", "coordination"]
TaskStatus = Literal["pending", "assigned", "in_progress", "done", "blocked"]


class TaskResponse(BaseModel):
    id: UUID
    event_request_id: UUID
    event_title: str | None = None
    title: str
    description: str | None = None
    task_type: TaskType
    assigned_to: UUID | None = None
    assignee_name: str | None = None
    due_at: datetime
    completed_at: datetime | None = None
    status: TaskStatus
    priority: int
    depends_on: UUID | None = None
    ai_generated: bool
    created_at: datetime


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to: UUID | None = None
    due_at: datetime | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=3)


class RoomLayoutItem(BaseModel):
    modelKey: str
    x: float
    y: float = 0.0
    z: float
    rotY: float = 0.0
    type: Literal["floor", "wall"] = "floor"
    surfaceY: float | None = None
    wallAxis: Literal["x", "z"] | None = None
    wallCoord: float | None = None
    isPositiveWall: bool | None = None
    mountY: float | None = None
    scale: dict[str, float] | None = None
    stackOn: int | None = None
    lxf: float | None = None
    lzf: float | None = None
    lx: float | None = None
    lz: float | None = None


class RoomLayoutResponse(BaseModel):
    id: UUID
    venue_id: UUID
    venue_name: str | None = None
    three_d_room_id: str | None = None
    event_request_id: UUID | None = None
    name: str
    items_json: list[RoomLayoutItem]
    item_count: int
    source: Literal["manual", "template", "ai_generated"]
    ai_prompt: str | None = None
    thumbnail_url: str | None = None
    is_current: bool
    created_at: datetime


class RoomLayoutCreateRequest(BaseModel):
    venue_id: UUID
    name: str = Field(min_length=2, max_length=255)
    items_json: list[RoomLayoutItem]
    source: Literal["manual", "template", "ai_generated"] = "manual"
    ai_prompt: str | None = None
    event_request_id: UUID | None = None


class AIChatRequest(BaseModel):
    message: str
    agent_type: Literal["copilot", "room_designer", "intake", "conflict_detector", "planner"] = "copilot"
    context: dict[str, Any] = Field(default_factory=dict)
    conversation_id: UUID | None = None


class AIChatResponse(BaseModel):
    response: str
    tool_calls_made: list[dict[str, Any]]
    conversation_id: UUID


class AIDesignRoomRequest(BaseModel):
    venue_name: str
    prompt: str
    event_request_id: UUID | None = None
    event_date_start: datetime | None = None
    event_date_end: datetime | None = None


class AIDetectConflictsRequest(BaseModel):
    request_id: UUID


class AIRunAgentRequest(BaseModel):
    agent_type: Literal["copilot", "room_designer", "intake", "conflict_detector", "planner"] = "copilot"
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    conversation_id: UUID | None = None


class AIAgentResponse(BaseModel):
    response: str
    agent_type: str
    tool_calls_made: list[dict[str, Any]]
    conversation_id: UUID | None = None
    iterations: int = 0


class AIStreamChunk(BaseModel):
    chunk_type: Literal["text", "tool_call", "done", "error"] = "text"
    content: str = ""
    tool_name: str | None = None
    tool_result: dict[str, Any] | None = None


class AIConversationSummary(BaseModel):
    id: UUID
    agent_type: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIConversationDetail(BaseModel):
    id: UUID
    agent_type: str
    messages: list[dict[str, Any]]
    context_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIToolInfo(BaseModel):
    name: str
    description: str
    agent_types: list[str]

