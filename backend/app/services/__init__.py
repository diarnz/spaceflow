from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Asset,
    AssetReservation,
    EventRequest,
    Quotation,
    RoomLayout,
    Task,
    User,
    Venue,
)
from app.schemas import (
    AssetAvailabilityResponse,
    AssetCreateRequest,
    AssetSummaryItem,
    AvailableSlot,
    BulkReserveRequest,
    BulkReserveResponse,
    BulkReserveResult,
    EventRequestCreate,
    EventRequestSummary,
    EventRequestUpdate,
    OccupiedSlot,
    QuotationLineItem,
    QuotationUpdateRequest,
    TaskResponse,
    TaskUpdateRequest,
    UserUpdateRequest,
    VenueAvailabilityResponse,
    VenueCreateRequest,
    VenueUpdateRequest,
)
from app.utils.auth import hash_password, verify_password


BOOKED_REQUEST_STATUSES = {"approved", "confirmed"}

THREE_D_ROOM_DIMENSIONS: dict[str, dict[str, float]] = {
    "lime-green-box": {"w": 5.5, "d": 3.2, "h": 2.6},
    "dark-green-box": {"w": 4.2, "d": 4.0, "h": 2.6},
    "orange-box": {"w": 8.0, "d": 4.2, "h": 3.0},
    "blue-box": {"w": 5.2, "d": 3.8, "h": 2.6},
}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"submitted", "cancelled"},
    "submitted": {"under_review", "cancelled"},
    "under_review": {"quotation_sent", "approved", "rejected", "cancelled"},
    "quotation_sent": {"approved", "rejected", "cancelled"},
    "approved": {"confirmed", "cancelled", "completed"},
    "confirmed": {"completed", "cancelled"},
    "rejected": set(),
    "cancelled": set(),
    "completed": set(),
}

SERVICE_FEES = {
    "conference": [("Event Coordination Staff", 2, Decimal("80.00")), ("Setup & Teardown Labor", 4, Decimal("50.00"))],
    "workshop": [("Workshop Facilitator Support", 1, Decimal("60.00")), ("Setup & Teardown Labor", 2, Decimal("50.00"))],
    "concert": [("Event Coordination Staff", 3, Decimal("80.00")), ("Setup & Teardown Labor", 6, Decimal("50.00")), ("Sound Engineering", 1, Decimal("200.00"))],
    "hackathon": [("Technical Staff On-Site", 2, Decimal("70.00")), ("Setup & Teardown Labor", 3, Decimal("50.00"))],
    "exhibition": [("Exhibition Setup Crew", 4, Decimal("60.00")), ("Event Coordination Staff", 1, Decimal("80.00"))],
    "dinner": [("Event Coordination Staff", 2, Decimal("80.00")), ("Setup & Teardown Labor", 2, Decimal("50.00"))],
    "private": [("Event Coordination Staff", 1, Decimal("80.00")), ("Setup & Teardown Labor", 2, Decimal("50.00"))],
    "other": [("Event Coordination Staff", 1, Decimal("80.00")), ("Setup & Teardown Labor", 2, Decimal("50.00"))],
}

TASK_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "conference": [
        {"title": "Confirm final attendee count with client", "task_type": "preparation", "priority": 1, "offset_from_start_hours": -72},
        {"title": "Verify all AV equipment (projector, microphones, screens)", "task_type": "preparation", "priority": 1, "offset_from_start_hours": -48},
        {"title": "Prepare event signage and directional materials", "task_type": "preparation", "priority": 2, "offset_from_start_hours": -48},
        {"title": "Confirm catering and refreshments", "task_type": "logistics", "priority": 2, "offset_from_start_hours": -48},
        {"title": "Deliver and arrange chairs per floor plan", "task_type": "setup", "priority": 1, "offset_from_start_hours": -2},
        {"title": "Set up tables per approved layout", "task_type": "setup", "priority": 1, "offset_from_start_hours": -2},
        {"title": "Configure AV system and test all connections", "task_type": "setup", "priority": 1, "offset_from_start_hours": -1},
        {"title": "Install signage at entrance and corridors", "task_type": "setup", "priority": 2, "offset_from_start_hours": -1},
        {"title": "Set up registration table at entrance", "task_type": "setup", "priority": 2, "offset_from_start_hours": -0.5},
        {"title": "Collect and return all chairs to storage", "task_type": "teardown", "priority": 1, "offset_from_end_hours": 1},
        {"title": "Break down and return all tables", "task_type": "teardown", "priority": 1, "offset_from_end_hours": 1},
        {"title": "Pack and return AV equipment to storage", "task_type": "teardown", "priority": 2, "offset_from_end_hours": 2},
        {"title": "Remove signage and restore venue", "task_type": "teardown", "priority": 2, "offset_from_end_hours": 2},
        {"title": "Final walkthrough and damage report", "task_type": "coordination", "priority": 2, "offset_from_end_hours": 2.5},
    ],
    "workshop": [
        {"title": "Prepare workshop materials", "task_type": "preparation", "priority": 1, "offset_from_start_hours": -48},
        {"title": "Test all laptops/PCs assigned to the room", "task_type": "preparation", "priority": 1, "offset_from_start_hours": -24},
        {"title": "Set up desks in workshop configuration", "task_type": "setup", "priority": 1, "offset_from_start_hours": -1.5},
        {"title": "Configure whiteboard and AV screen", "task_type": "setup", "priority": 1, "offset_from_start_hours": -1},
        {"title": "Clear and restore room after workshop", "task_type": "teardown", "priority": 1, "offset_from_end_hours": 1},
        {"title": "Collect equipment and store in designated area", "task_type": "teardown", "priority": 2, "offset_from_end_hours": 1.5},
    ],
    "hackathon": [
        {"title": "Confirm team count and assign pod positions", "task_type": "preparation", "priority": 1, "offset_from_start_hours": -48},
        {"title": "Test all PCs and ensure network connectivity", "task_type": "preparation", "priority": 1, "offset_from_start_hours": -24},
        {"title": "Set up hackathon pods (tables + chairs + PCs)", "task_type": "setup", "priority": 1, "offset_from_start_hours": -2},
        {"title": "Place whiteboards and label team areas", "task_type": "setup", "priority": 2, "offset_from_start_hours": -1},
        {"title": "Install power strips at each pod", "task_type": "setup", "priority": 1, "offset_from_start_hours": -1},
        {"title": "Collect all equipment post-hackathon", "task_type": "teardown", "priority": 1, "offset_from_end_hours": 2},
        {"title": "Return PCs and peripherals to IT storage", "task_type": "teardown", "priority": 1, "offset_from_end_hours": 3},
    ],
    "concert": [
        {"title": "Confirm stage panel setup and dimensions", "task_type": "preparation", "priority": 1, "offset_from_start_hours": -72},
        {"title": "Sound check with performers", "task_type": "preparation", "priority": 1, "offset_from_start_hours": -4},
        {"title": "Assemble stage panels", "task_type": "setup", "priority": 1, "offset_from_start_hours": -4},
        {"title": "Configure PA system and lighting rig", "task_type": "setup", "priority": 1, "offset_from_start_hours": -3},
        {"title": "Set up audience seating per capacity", "task_type": "setup", "priority": 1, "offset_from_start_hours": -2},
        {"title": "Post-concert venue restoration", "task_type": "teardown", "priority": 1, "offset_from_end_hours": 2},
        {"title": "Disassemble and store stage panels", "task_type": "teardown", "priority": 1, "offset_from_end_hours": 3},
    ],
}


@dataclass
class Conflict:
    type: str
    severity: str
    description: str
    affected_request_ids: list[str]
    affected_asset_id: str | None = None
    asset_name: str | None = None
    available: int | None = None
    requested: int | None = None
    suggestion: str | None = None


def combine_date_time(d: date, t: time) -> datetime:
    return datetime.combine(d, t).replace(tzinfo=timezone.utc)


def event_window(req: EventRequest) -> tuple[datetime, datetime]:
    start = combine_date_time(req.requested_date, req.start_time) - timedelta(minutes=req.setup_time_minutes)
    end = combine_date_time(req.requested_date, req.end_time) + timedelta(minutes=req.teardown_time_minutes)
    return start, end


def _mins_to_str(mins: int) -> str:
    h, m = divmod(mins, 60)
    return f"{h:02d}:{m:02d}"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _fallback_full_name(email: str) -> str:
    local = email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    return local.title() or "SpaceFlow User"


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    normalized = normalize_email(email)
    return await db.scalar(select(User).where(func.lower(User.email) == normalized))


async def upsert_external_auth_user(
    *,
    email: str,
    full_name: str | None,
    phone: str | None,
    organization: str | None,
    db: AsyncSession,
    is_active: bool = True,
) -> User:
    normalized = normalize_email(email)
    user = await get_user_by_email(normalized, db)

    if user:
        if user.role in {"admin", "staff"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This staff account is not linked to Supabase sign-in. Use the existing internal login.",
            )
        user.email = normalized
        if full_name:
            user.full_name = full_name
        if phone:
            user.phone = phone
        if organization:
            user.organization = organization
        user.is_active = is_active
        await db.commit()
        await db.refresh(user)
        return user

    user = User(
        email=normalized,
        hashed_password=None,
        full_name=full_name or _fallback_full_name(normalized),
        role="client",
        phone=phone,
        organization=organization,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def register_user(*, email: str, password: str, full_name: str, phone: str | None, organization: str | None, db: AsyncSession) -> User:
    normalized = normalize_email(email)
    existing = await get_user_by_email(normalized, db)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    user = User(
        email=normalized,
        hashed_password=hash_password(password),
        full_name=full_name,
        phone=phone,
        organization=organization,
        role="client",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_profile(user: User, data: UserUpdateRequest, db: AsyncSession) -> User:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User:
    normalized = normalize_email(email)
    user = await db.scalar(select(User).where(func.lower(User.email) == normalized, User.is_active.is_(True)))
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    return user


async def list_venues(db: AsyncSession, *, active_only: bool = True) -> list[Venue]:
    stmt = select(Venue)
    if active_only:
        stmt = stmt.where(Venue.status == "active")
    stmt = stmt.order_by(Venue.floor, Venue.name)
    return list((await db.scalars(stmt)).all())


async def get_venue(venue_id: UUID, db: AsyncSession) -> Venue:
    venue = await db.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found.")
    return venue


async def create_venue(data: VenueCreateRequest, db: AsyncSession) -> Venue:
    venue = Venue(**data.model_dump())
    db.add(venue)
    await db.commit()
    await db.refresh(venue)
    return venue


async def update_venue(venue_id: UUID, data: VenueUpdateRequest, db: AsyncSession) -> Venue:
    venue = await get_venue(venue_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(venue, field, value)
    await db.commit()
    await db.refresh(venue)
    return venue


async def get_venue_availability(venue_id: UUID, check_date: date, duration_hours: float, db: AsyncSession) -> VenueAvailabilityResponse:
    await get_venue(venue_id, db)
    stmt = select(EventRequest).where(
        EventRequest.venue_id == venue_id,
        EventRequest.requested_date == check_date,
        EventRequest.status.in_(BOOKED_REQUEST_STATUSES),
    )
    events = list((await db.scalars(stmt)).all())
    blocked: list[tuple[int, int, EventRequest]] = []
    for ev in events:
        start = ev.start_time.hour * 60 + ev.start_time.minute - ev.setup_time_minutes
        end = ev.end_time.hour * 60 + ev.end_time.minute + ev.teardown_time_minutes
        blocked.append((max(0, start), min(24 * 60, end), ev))
    blocked.sort(key=lambda item: item[0])

    day_start = 7 * 60
    day_end = 23 * 60
    duration_min = int(duration_hours * 60)
    cursor = day_start
    available_slots: list[AvailableSlot] = []
    occupied_slots: list[OccupiedSlot] = []

    for b_start, b_end, ev in blocked:
        if cursor < b_start and (b_start - cursor) >= duration_min:
            available_slots.append(AvailableSlot(start=_mins_to_str(cursor), end=_mins_to_str(b_start)))
        occupied_slots.append(
            OccupiedSlot(
                start=f"{ev.start_time.hour:02d}:{ev.start_time.minute:02d}",
                end=f"{ev.end_time.hour:02d}:{ev.end_time.minute:02d}",
                event_request_id=ev.id,
                event_title=ev.title,
                attendees=ev.attendee_count,
            )
        )
        cursor = max(cursor, b_end)

    if cursor < day_end and (day_end - cursor) >= duration_min:
        available_slots.append(AvailableSlot(start=_mins_to_str(cursor), end=_mins_to_str(day_end)))

    return VenueAvailabilityResponse(
        venue_id=venue_id,
        date=check_date,
        duration_hours=duration_hours,
        available_slots=available_slots,
        occupied_slots=occupied_slots,
        is_fully_available=not occupied_slots,
    )


async def create_request(data: EventRequestCreate, client_id: UUID, db: AsyncSession) -> EventRequest:
    req = EventRequest(client_id=client_id, status="submitted", **data.model_dump())
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


async def get_request(request_id: UUID, db: AsyncSession) -> EventRequest:
    req = await db.get(EventRequest, request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    return req


async def list_requests(
    db: AsyncSession,
    *,
    current_user: User,
    status_filter: str | None = None,
    venue_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[EventRequest], int]:
    filters = []
    if current_user.role == "client":
        filters.append(EventRequest.client_id == current_user.id)
    if status_filter:
        filters.append(EventRequest.status == status_filter)
    if venue_id:
        filters.append(EventRequest.venue_id == venue_id)

    stmt = select(EventRequest)
    if filters:
        stmt = stmt.where(*filters)

    total_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(await db.scalar(total_stmt) or 0)
    rows = list((await db.scalars(stmt.order_by(desc(EventRequest.created_at)).offset(offset).limit(limit))).all())
    return rows, total


async def update_request(request_id: UUID, data: EventRequestUpdate, current_user: User, db: AsyncSession) -> EventRequest:
    req = await get_request(request_id, db)
    if current_user.role == "client":
        if req.client_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your request.")
        if req.status not in {"draft", "submitted"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Clients can only edit draft or submitted requests.")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(req, field, value)
    await db.commit()
    await db.refresh(req)
    return req


async def assign_venue(request_id: UUID, venue_id: UUID, db: AsyncSession) -> EventRequest:
    req = await get_request(request_id, db)
    await get_venue(venue_id, db)
    req.venue_id = venue_id
    if req.status == "submitted":
        req.status = "under_review"
    await db.commit()
    await db.refresh(req)
    return req


async def transition_request_status(request_id: UUID, new_status: str, *, reason: str | None = None, db: AsyncSession) -> tuple[str, EventRequest]:
    req = await get_request(request_id, db)
    previous_status = req.status
    if new_status not in ALLOWED_TRANSITIONS.get(previous_status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from '{previous_status}' to '{new_status}'.",
        )
    req.status = new_status
    if new_status == "rejected":
        req.rejection_reason = reason
    await db.commit()
    await db.refresh(req)
    return previous_status, req


async def update_ai_proposal(request_id: UUID, proposal: dict[str, Any], db: AsyncSession) -> EventRequest:
    req = await get_request(request_id, db)
    req.ai_proposal_json = proposal
    await db.commit()
    await db.refresh(req)
    return req


async def get_asset(asset_id: UUID, db: AsyncSession) -> Asset:
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    return asset


async def list_assets(db: AsyncSession, *, category: str | None = None, active_only: bool = True) -> list[Asset]:
    stmt = select(Asset)
    if active_only:
        stmt = stmt.where(Asset.is_active.is_(True))
    if category:
        stmt = stmt.where(Asset.category == category)
    stmt = stmt.order_by(Asset.category, Asset.name)
    return list((await db.scalars(stmt)).all())


async def create_asset(data: AssetCreateRequest, db: AsyncSession) -> Asset:
    asset = Asset(**data.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def get_reserved_quantity(
    asset_id: UUID,
    start: datetime,
    end: datetime,
    db: AsyncSession,
    *,
    exclude_request_id: UUID | None = None,
) -> int:
    stmt = select(func.coalesce(func.sum(AssetReservation.quantity_confirmed), 0)).where(
        AssetReservation.asset_id == asset_id,
        AssetReservation.status.in_(["pending", "confirmed"]),
        AssetReservation.reservation_start < end,
        AssetReservation.reservation_end > start,
    )
    if exclude_request_id:
        stmt = stmt.where(AssetReservation.event_request_id != exclude_request_id)
    return int(await db.scalar(stmt) or 0)


async def get_asset_availability(asset_id: UUID, start: datetime, end: datetime, db: AsyncSession) -> AssetAvailabilityResponse:
    asset = await get_asset(asset_id, db)
    reserved = await get_reserved_quantity(asset_id, start, end, db)
    available = max(0, asset.total_quantity - reserved)

    reservations = list(
        (
            await db.scalars(
                select(AssetReservation).where(
                    AssetReservation.asset_id == asset_id,
                    AssetReservation.status.in_(["pending", "confirmed"]),
                    AssetReservation.reservation_start < end,
                    AssetReservation.reservation_end > start,
                )
            )
        ).all()
    )

    return AssetAvailabilityResponse(
        asset_id=asset.id,
        asset_name=asset.name,
        total_quantity=asset.total_quantity,
        reserved_quantity=reserved,
        available_quantity=available,
        is_available=available > 0,
        reservations_in_window=[
            {
                "event_request_id": str(r.event_request_id),
                "quantity_requested": r.quantity_requested,
                "quantity_confirmed": r.quantity_confirmed,
                "status": r.status,
            }
            for r in reservations
        ],
    )


async def get_assets_summary(db: AsyncSession) -> list[AssetSummaryItem]:
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=7)
    assets = await list_assets(db)
    summary: list[AssetSummaryItem] = []
    for asset in assets:
        reserved = await get_reserved_quantity(asset.id, now, future, db)
        available = max(0, asset.total_quantity - reserved)
        summary.append(
            AssetSummaryItem(
                asset_id=asset.id,
                name=asset.name,
                category=asset.category,
                total_quantity=asset.total_quantity,
                available_quantity=available,
                reserved_quantity=reserved,
                availability_pct=(available / asset.total_quantity) if asset.total_quantity else 0.0,
                has_conflict_next_7_days=reserved > asset.total_quantity,
            )
        )
    return summary


async def bulk_reserve_for_request(request_id: UUID, data: BulkReserveRequest, db: AsyncSession) -> BulkReserveResponse:
    req = await get_request(request_id, db)
    reservation_start, reservation_end = event_window(req)
    can_fulfill_all = True
    results: list[BulkReserveResult] = []

    for item in data.assets:
        asset = await get_asset(item.asset_id, db)
        reserved = await get_reserved_quantity(asset.id, reservation_start, reservation_end, db, exclude_request_id=request_id)
        available = max(0, asset.total_quantity - reserved)
        confirmed = min(item.quantity, available)

        existing = await db.scalar(
            select(AssetReservation).where(
                AssetReservation.event_request_id == request_id,
                AssetReservation.asset_id == asset.id,
            )
        )

        if existing:
            existing.quantity_requested = item.quantity
            existing.quantity_confirmed = confirmed
            existing.reservation_start = reservation_start
            existing.reservation_end = reservation_end
            existing.status = "pending"
        else:
            db.add(
                AssetReservation(
                    event_request_id=request_id,
                    asset_id=asset.id,
                    quantity_requested=item.quantity,
                    quantity_confirmed=confirmed,
                    reservation_start=reservation_start,
                    reservation_end=reservation_end,
                    status="pending",
                )
            )

        shortfall = max(0, item.quantity - confirmed)
        if shortfall:
            can_fulfill_all = False
        results.append(
            BulkReserveResult(
                asset_id=asset.id,
                name=asset.name,
                requested=item.quantity,
                confirmed=confirmed,
                status="fulfilled" if shortfall == 0 else "partial",
                shortfall=shortfall or None,
                conflict_reason=None
                if shortfall == 0
                else f"Only {available} available in the requested time window.",
            )
        )

    await db.commit()
    return BulkReserveResponse(can_fulfill_all=can_fulfill_all, results=results)


async def list_reservations_for_request(request_id: UUID, db: AsyncSession) -> list[AssetReservation]:
    stmt = select(AssetReservation).where(AssetReservation.event_request_id == request_id).order_by(AssetReservation.created_at)
    return list((await db.scalars(stmt)).all())


async def confirm_reservations_for_request(request_id: UUID, db: AsyncSession) -> None:
    reservations = await list_reservations_for_request(request_id, db)
    for reservation in reservations:
        reservation.status = "confirmed"
    await db.commit()


def times_overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
    return start1 < end2 and end1 > start2


async def check_conflicts(request_id: UUID, db: AsyncSession) -> list[Conflict]:
    req = await get_request(request_id, db)
    conflicts: list[Conflict] = []

    if req.venue_id:
        same_day_stmt = select(EventRequest).where(
            EventRequest.venue_id == req.venue_id,
            EventRequest.id != req.id,
            EventRequest.requested_date == req.requested_date,
            EventRequest.status.in_(BOOKED_REQUEST_STATUSES),
        )
        for other in list((await db.scalars(same_day_stmt)).all()):
            if times_overlap(req.start_time, req.end_time, other.start_time, other.end_time):
                conflicts.append(
                    Conflict(
                        type="venue_double_booking",
                        severity="blocking",
                        description=f"Venue already booked for '{other.title}' ({other.start_time:%H:%M}-{other.end_time:%H:%M}).",
                        affected_request_ids=[str(other.id)],
                        suggestion="Choose another venue or move the request to a different time slot.",
                    )
                )
            else:
                req_start, req_end = event_window(req)
                other_start, other_end = event_window(other)
                if req_start < other_end and req_end > other_start:
                    conflicts.append(
                        Conflict(
                            type="setup_teardown_overlap",
                            severity="warning",
                            description=f"Setup/teardown window overlaps with '{other.title}'.",
                            affected_request_ids=[str(other.id)],
                            suggestion="Reduce buffer windows or insert more time between events.",
                        )
                    )

    reservations = await list_reservations_for_request(req.id, db)
    for reservation in reservations:
        asset = await get_asset(reservation.asset_id, db)
        other_reserved = await get_reserved_quantity(
            asset.id,
            reservation.reservation_start,
            reservation.reservation_end,
            db,
            exclude_request_id=req.id,
        )
        available = max(0, asset.total_quantity - other_reserved)
        if reservation.quantity_requested > available:
            conflicts.append(
                Conflict(
                    type="asset_over_reservation",
                    severity="blocking",
                    description=f"Asset '{asset.name}' requested: {reservation.quantity_requested}, available: {available}.",
                    affected_request_ids=[],
                    affected_asset_id=str(asset.id),
                    asset_name=asset.name,
                    available=available,
                    requested=reservation.quantity_requested,
                    suggestion=f"Reduce allocation to {available} or substitute with a different asset type.",
                )
            )

    if req.assigned_staff_id:
        staff_stmt = select(EventRequest).where(
            EventRequest.assigned_staff_id == req.assigned_staff_id,
            EventRequest.id != req.id,
            EventRequest.requested_date == req.requested_date,
            EventRequest.status.in_(BOOKED_REQUEST_STATUSES),
        )
        others = list((await db.scalars(staff_stmt)).all())
        if others:
            conflicts.append(
                Conflict(
                    type="staff_double_assignment",
                    severity="warning",
                    description="Assigned staff member already has another active event on the same day.",
                    affected_request_ids=[str(other.id) for other in others],
                    suggestion="Reassign staff or rebalance operational load.",
                )
            )

    return conflicts


def conflicts_to_dict(conflicts: list[Conflict]) -> list[dict[str, Any]]:
    return [
        {
            "type": c.type,
            "severity": c.severity,
            "description": c.description,
            "affected_request_ids": c.affected_request_ids,
            "affected_asset_id": c.affected_asset_id,
            "asset_name": c.asset_name,
            "available": c.available,
            "requested": c.requested,
            "suggestion": c.suggestion,
        }
        for c in conflicts
    ]


def event_duration_hours(start: time, end: time) -> Decimal:
    minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    return Decimal(str(minutes / 60))


async def generate_quotation(request_id: UUID, db: AsyncSession, *, created_by: UUID | None = None, generated_by_ai: bool = False) -> Quotation:
    req = await get_request(request_id, db)
    line_items: list[QuotationLineItem] = []

    if req.venue_id:
        venue = await get_venue(req.venue_id, db)
        venue_total = venue.base_price_per_hour * event_duration_hours(req.start_time, req.end_time)
        line_items.append(
            QuotationLineItem(
                category="venue",
                name=f"{venue.name} - {event_duration_hours(req.start_time, req.end_time)} hours",
                qty=1,
                unit_price=venue_total,
                total=venue_total,
            )
        )

    for reservation in await list_reservations_for_request(request_id, db):
        if reservation.quantity_confirmed <= 0:
            continue
        asset = await get_asset(reservation.asset_id, db)
        total = asset.unit_price * reservation.quantity_confirmed
        line_items.append(
            QuotationLineItem(
                category=asset.category,
                name=asset.name,
                qty=reservation.quantity_confirmed,
                unit_price=asset.unit_price,
                total=total,
            )
        )

    for label, qty, unit in SERVICE_FEES.get(req.event_type, SERVICE_FEES["other"]):
        line_items.append(
            QuotationLineItem(
                category="service",
                name=label,
                qty=qty,
                unit_price=unit,
                total=unit * qty,
            )
        )

    subtotal = sum((item.total for item in line_items), Decimal("0"))
    tax_rate = Decimal("0.20")
    tax_amount = (subtotal * tax_rate).quantize(Decimal("0.01"))
    total_amount = subtotal + tax_amount

    quotation = Quotation(
        event_request_id=request_id,
        line_items=[item.model_dump(mode="json") for item in line_items],
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total_amount=total_amount,
        valid_until=req.requested_date + timedelta(days=14),
        status="draft",
        generated_by_ai=generated_by_ai,
        created_by=created_by,
    )
    db.add(quotation)
    await db.commit()
    await db.refresh(quotation)
    return quotation


async def get_quotation(quotation_id: UUID, db: AsyncSession) -> Quotation:
    quotation = await db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
    return quotation


async def update_quotation(quotation_id: UUID, data: QuotationUpdateRequest, db: AsyncSession) -> Quotation:
    quotation = await get_quotation(quotation_id, db)
    if data.line_items is not None:
        quotation.line_items = [item.model_dump(mode="json") for item in data.line_items]
    if data.admin_notes is not None:
        quotation.admin_notes = data.admin_notes
    if data.tax_rate is not None:
        quotation.tax_rate = data.tax_rate

    subtotal = sum((Decimal(str(item["total"])) for item in quotation.line_items), Decimal("0"))
    tax_amount = (subtotal * quotation.tax_rate).quantize(Decimal("0.01"))
    quotation.subtotal = subtotal
    quotation.tax_amount = tax_amount
    quotation.total_amount = subtotal + tax_amount
    await db.commit()
    await db.refresh(quotation)
    return quotation


async def send_quotation(quotation_id: UUID, db: AsyncSession) -> Quotation:
    quotation = await get_quotation(quotation_id, db)
    quotation.status = "sent"
    quotation.sent_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(quotation)
    return quotation


async def generate_tasks_for_request(request_id: UUID, db: AsyncSession, *, ai_generated: bool = False) -> list[Task]:
    req = await get_request(request_id, db)
    template = TASK_TEMPLATES.get(req.event_type, TASK_TEMPLATES["conference"])
    await db.execute(delete(Task).where(Task.event_request_id == request_id, Task.ai_generated.is_(False)))

    event_start = combine_date_time(req.requested_date, req.start_time)
    event_end = combine_date_time(req.requested_date, req.end_time)

    created: list[Task] = []
    for item in template:
        if "offset_from_start_hours" in item:
            due_at = event_start + timedelta(hours=item["offset_from_start_hours"])
        else:
            due_at = event_end + timedelta(hours=item["offset_from_end_hours"])
        task = Task(
            event_request_id=request_id,
            title=item["title"],
            task_type=item["task_type"],
            due_at=due_at,
            priority=item["priority"],
            status="pending",
            ai_generated=ai_generated,
        )
        db.add(task)
        created.append(task)

    await db.commit()
    for task in created:
        await db.refresh(task)
    return created


async def list_tasks(
    db: AsyncSession,
    *,
    request_id: UUID | None = None,
    assigned_to: UUID | None = None,
    status_filter: str | None = None,
) -> list[Task]:
    stmt = select(Task)
    if request_id:
        stmt = stmt.where(Task.event_request_id == request_id)
    if assigned_to:
        stmt = stmt.where(Task.assigned_to == assigned_to)
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    stmt = stmt.order_by(Task.due_at, Task.priority)
    return list((await db.scalars(stmt)).all())


async def get_task(task_id: UUID, db: AsyncSession) -> Task:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


async def update_task(task_id: UUID, data: TaskUpdateRequest, db: AsyncSession) -> Task:
    task = await get_task(task_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    if task.status == "done" and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return task


async def complete_task(task_id: UUID, db: AsyncSession) -> Task:
    task = await get_task(task_id, db)
    task.status = "done"
    task.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return task


async def list_layouts_for_venue(venue_id: UUID, db: AsyncSession) -> list[RoomLayout]:
    stmt = select(RoomLayout).where(RoomLayout.venue_id == venue_id).order_by(desc(RoomLayout.created_at))
    return list((await db.scalars(stmt)).all())


async def get_current_layout(three_d_room_id: str, db: AsyncSession) -> RoomLayout | None:
    venue = await db.scalar(select(Venue).where(Venue.three_d_room_id == three_d_room_id))
    if not venue:
        return None
    stmt = (
        select(RoomLayout)
        .where(RoomLayout.venue_id == venue.id, RoomLayout.is_current.is_(True))
        .order_by(desc(RoomLayout.created_at))
    )
    return await db.scalar(stmt)


async def deactivate_current_layouts(venue_id: UUID, db: AsyncSession) -> None:
    layouts = await list_layouts_for_venue(venue_id, db)
    for layout in layouts:
        if layout.is_current:
            layout.is_current = False


async def sync_layout_from_3d(three_d_room_id: str, items: list[dict[str, Any]], db: AsyncSession, *, name: str = "Manual Save") -> RoomLayout | None:
    venue = await db.scalar(select(Venue).where(Venue.three_d_room_id == three_d_room_id))
    if not venue:
        return None
    await deactivate_current_layouts(venue.id, db)
    layout = RoomLayout(venue_id=venue.id, name=name, items_json=items, source="manual", is_current=True)
    db.add(layout)
    await db.commit()
    await db.refresh(layout)
    return layout


async def save_ai_layout(
    *,
    three_d_room_id: str,
    items: list[dict[str, Any]],
    ai_prompt: str,
    layout_name: str,
    event_request_id: UUID | None,
    db: AsyncSession,
) -> RoomLayout | None:
    venue = await db.scalar(select(Venue).where(Venue.three_d_room_id == three_d_room_id))
    if not venue:
        return None
    await deactivate_current_layouts(venue.id, db)
    layout = RoomLayout(
        venue_id=venue.id,
        event_request_id=event_request_id,
        name=layout_name,
        items_json=items,
        source="ai_generated",
        ai_prompt=ai_prompt,
        is_current=True,
    )
    db.add(layout)
    await db.commit()
    await db.refresh(layout)
    return layout


def build_request_summary(req: EventRequest) -> EventRequestSummary:
    return EventRequestSummary(
        id=req.id,
        title=req.title,
        event_type=req.event_type,
        status=req.status,
        requested_date=req.requested_date,
        start_time=req.start_time,
        end_time=req.end_time,
        attendee_count=req.attendee_count,
        venue_id=req.venue_id,
        venue_name=req.venue.name if req.venue else None,
        client_id=req.client_id,
        client_name=req.client.full_name if req.client else None,
        has_ai_proposal=req.ai_proposal_json is not None,
        has_conflicts=bool(req.ai_proposal_json and req.ai_proposal_json.get("conflicts")),
        created_at=req.created_at,
    )


async def get_request_context(request_id: UUID, db: AsyncSession) -> dict[str, Any]:
    req = await get_request(request_id, db)
    conflicts = await check_conflicts(request_id, db)
    latest_quotation = await db.scalar(
        select(Quotation).where(Quotation.event_request_id == request_id).order_by(desc(Quotation.created_at))
    )
    tasks = await list_tasks(db, request_id=request_id)
    reservations = await list_reservations_for_request(request_id, db)
    return {
        "request": req,
        "conflicts": conflicts,
        "quotation": latest_quotation,
        "tasks": tasks,
        "reservations": reservations,
    }


def build_task_response(task: Task, event_title: str | None = None, assignee_name: str | None = None) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        event_request_id=task.event_request_id,
        event_title=event_title,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        assigned_to=task.assigned_to,
        assignee_name=assignee_name,
        due_at=task.due_at,
        completed_at=task.completed_at,
        status=task.status,
        priority=task.priority,
        depends_on=task.depends_on,
        ai_generated=task.ai_generated,
        created_at=task.created_at,
    )
