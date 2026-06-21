from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_staff
from app.models import EventRequest, User
from app.schemas import TaskResponse, TaskUpdateRequest, UserResponse
from app.services import build_task_response, complete_task, generate_tasks_for_request, list_tasks, update_task


router = APIRouter()


async def _serialize_tasks(tasks, db: AsyncSession) -> list[TaskResponse]:
    output: list[TaskResponse] = []
    for task in tasks:
        event = await db.get(EventRequest, task.event_request_id)
        assignee = await db.get(User, task.assigned_to) if task.assigned_to else None
        output.append(
            build_task_response(
                task,
                event.title if event else None,
                assignee.full_name if assignee else None,
                event.venue.name if event and event.venue else None,
                event.attendee_count if event else 1,
            )
        )
    return output


@router.post("/generate/{request_id}", response_model=list[TaskResponse], status_code=201)
async def route_generate_tasks(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[TaskResponse]:
    tasks = await generate_tasks_for_request(request_id, db, ai_generated=True)
    return await _serialize_tasks(tasks, db)


@router.get("", response_model=list[TaskResponse])
async def route_list_tasks(
    request_id: UUID | None = Query(None),
    assigned_to: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[TaskResponse]:
    tasks = await list_tasks(db, request_id=request_id, assigned_to=assigned_to, status_filter=status_filter)
    return await _serialize_tasks(tasks, db)


@router.get("/my-tasks", response_model=list[TaskResponse])
async def route_my_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    tasks = await list_tasks(db, assigned_to=current_user.id)
    return await _serialize_tasks([task for task in tasks if task.status != "done"], db)


@router.get("/workers", response_model=list[UserResponse])
async def route_list_workers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[UserResponse]:
    workers = await db.scalars(
        select(User)
        .where(User.role.in_(("admin", "staff")), User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return [UserResponse.model_validate(worker) for worker in workers]


@router.put("/{task_id}", response_model=TaskResponse)
async def route_update_task(
    task_id: UUID,
    data: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TaskResponse:
    task = await update_task(task_id, data, db)
    return (await _serialize_tasks([task], db))[0]


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def route_complete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TaskResponse:
    task = await complete_task(task_id, db)
    return (await _serialize_tasks([task], db))[0]
