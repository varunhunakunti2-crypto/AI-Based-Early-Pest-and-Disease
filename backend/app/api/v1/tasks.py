"""Inspection task API routes (Uber-style intelligent distribution).

Endpoints for task creation, assignment, acceptance, and lifecycle management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_principal
from app.core.errors import ApiError
from app.db.models import User
from app.db.session import get_db
from app.geo.task_service import (
    STATUS_ACCEPTED,
    STATUS_AVAILABLE,
    STATUS_COMPLETED,
    STATUS_CREATED,
    TaskServiceError,
    accept_task,
    complete_task,
    create_inspection_task,
    decline_task,
    expire_overdue_tasks,
    find_eligible_users,
    get_available_tasks,
    get_user_tasks,
    reassign_task,
    submit_task,
    start_task,
)

router = APIRouter(tags=["tasks"])


class TaskCreateRequest(BaseModel):
    h3_cell_id: str
    crop_code: str
    target_code: str
    task_type: str = Field(
        pattern="^(hotspot_verification|routine_scouting|recovery_inspection|expert_review)$"
    )
    priority: str = Field(default="moderate", pattern="^(low|moderate|high|urgent)$")
    deadline_hours: Optional[int] = Field(default=None, ge=1, le=720)
    suspected_issue: Optional[str] = Field(default=None, max_length=500)
    crop_growth_stage: Optional[str] = Field(default=None, max_length=50)
    inspection_instructions: Optional[str] = Field(default=None, max_length=2000)
    max_distance_km: Optional[float] = Field(default=None, gt=0, le=100)
    required_expertise: list[str] = Field(default_factory=list)
    assignment_type: str = Field(default="automatic", pattern="^(automatic|voluntary)$")


class TaskResponse(BaseModel):
    task_id: str
    h3_cell_id: str
    crop_code: str
    target_code: str
    task_type: str
    priority: str
    status: str
    assignment_type: str
    deadline: Optional[str]
    suspected_issue: Optional[str]
    created_at: str


class TaskAcceptRequest(BaseModel):
    task_id: str


class TaskDeclineRequest(BaseModel):
    task_id: str


class TaskStartRequest(BaseModel):
    task_id: str


class TaskSubmitRequest(BaseModel):
    task_id: str


class TaskCompleteRequest(BaseModel):
    task_id: str
    verified: bool = True


class TaskReassignRequest(BaseModel):
    task_id: str
    new_user_id: str
    reason: Optional[str] = None


class EligibleUserResponse(BaseModel):
    user_id: str
    distance_km: Optional[float]
    current_workload: int
    max_concurrent_tasks: int
    completion_rate: float
    expertise_areas: list[str]
    crop_experience: list[str]
    has_availability: bool
    is_available: bool


class AvailableTaskResponse(BaseModel):
    task_id: str
    h3_cell_id: str
    crop_code: str
    target_code: str
    task_type: str
    priority: str
    deadline: Optional[str]
    suspected_issue: Optional[str]
    distance_km: Optional[float]
    created_at: str


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Create a new inspection task."""
    try:
        task = create_inspection_task(
            db=db,
            h3_cell_id=payload.h3_cell_id,
            crop_code=payload.crop_code,
            target_code=payload.target_code,
            task_type=payload.task_type,
            priority=payload.priority,
            created_by=user.id,
            deadline_hours=payload.deadline_hours,
            suspected_issue=payload.suspected_issue,
            crop_growth_stage=payload.crop_growth_stage,
            inspection_instructions=payload.inspection_instructions,
            max_distance_km=payload.max_distance_km,
            required_expertise=payload.required_expertise,
            assignment_type=payload.assignment_type,
        )
    except TaskServiceError as exc:
        raise ApiError(400, "task_error", str(exc)) from exc
    db.commit()
    return TaskResponse(
        task_id=task.id,
        h3_cell_id=task.h3_cell_id,
        crop_code=task.crop_code,
        target_code=task.target_code,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        assignment_type=task.assignment_type,
        deadline=task.deadline.isoformat() if task.deadline else None,
        suspected_issue=task.suspected_issue,
        created_at=task.created_at.isoformat(),
    )


@router.get("/available", response_model=list[AvailableTaskResponse])
def list_available_tasks(
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[AvailableTaskResponse]:
    """List tasks available for voluntary acceptance by the current user."""
    tasks = get_available_tasks(db, user_id=user.id, limit=limit)
    return [AvailableTaskResponse(**t) for t in tasks]


@router.get("/my-tasks", response_model=list[TaskResponse])
def list_my_tasks(
    status: Optional[str] = Query(default=None, pattern="^(CREATED|AVAILABLE|ASSIGNED|ACCEPTED|IN_PROGRESS|SUBMITTED|UNDER_REVIEW|VERIFIED|COMPLETED|REJECTED|CANCELLED|EXPIRED|REASSIGNED)$"),
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[TaskResponse]:
    """List tasks assigned to the current user."""
    tasks = get_user_tasks(db, user_id=user.id, status_filter=status, limit=limit)
    return [TaskResponse(**t) for t in tasks]


@router.post("/{task_id}/accept", response_model=TaskResponse)
def accept_task_endpoint(
    task_id: str = Path(..., description="Task ID"),
    payload: TaskAcceptRequest | None = None,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Accept an available inspection task."""
    if payload is None:
        payload = TaskAcceptRequest(task_id=task_id)
    elif payload.task_id != task_id:
        raise ApiError(400, "task_id_mismatch", "Task ID in body does not match path")

    try:
        task = accept_task(db, task_id=task_id, user_id=user.id)
    except TaskServiceError as exc:
        raise ApiError(400, "task_error", str(exc)) from exc
    db.commit()
    return TaskResponse(
        task_id=task.id,
        h3_cell_id=task.h3_cell_id,
        crop_code=task.crop_code,
        target_code=task.target_code,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        assignment_type=task.assignment_type,
        deadline=task.deadline.isoformat() if task.deadline else None,
        suspected_issue=task.suspected_issue,
        created_at=task.created_at.isoformat(),
    )


@router.post("/{task_id}/decline")
def decline_task_endpoint(
    task_id: str = Path(..., description="Task ID"),
    payload: TaskDeclineRequest | None = None,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Decline an available task."""
    if payload is None:
        payload = TaskDeclineRequest(task_id=task_id)

    try:
        decline_task(db, task_id=task_id, user_id=user.id)
    except TaskServiceError as exc:
        raise ApiError(400, "task_error", str(exc)) from exc
    db.commit()
    return {"task_id": task_id, "status": "declined", "declined_by": user.id}


@router.post("/{task_id}/start", response_model=TaskResponse)
def start_task_endpoint(
    task_id: str = Path(..., description="Task ID"),
    payload: TaskStartRequest | None = None,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Start an accepted task (move to IN_PROGRESS)."""
    if payload is None:
        payload = TaskStartRequest(task_id=task_id)

    try:
        task = start_task(db, task_id=task_id, user_id=user.id)
    except TaskServiceError as exc:
        raise ApiError(400, "task_error", str(exc)) from exc
    db.commit()
    return TaskResponse(
        task_id=task.id,
        h3_cell_id=task.h3_cell_id,
        crop_code=task.crop_code,
        target_code=task.target_code,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        assignment_type=task.assignment_type,
        deadline=task.deadline.isoformat() if task.deadline else None,
        suspected_issue=task.suspected_issue,
        created_at=task.created_at.isoformat(),
    )


@router.post("/{task_id}/submit", response_model=TaskResponse)
def submit_task_endpoint(
    task_id: str = Path(..., description="Task ID"),
    payload: TaskSubmitRequest | None = None,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Submit a completed task for review."""
    if payload is None:
        payload = TaskSubmitRequest(task_id=task_id)

    try:
        task = submit_task(db, task_id=task_id, user_id=user.id)
    except TaskServiceError as exc:
        raise ApiError(400, "task_error", str(exc)) from exc
    db.commit()
    return TaskResponse(
        task_id=task.id,
        h3_cell_id=task.h3_cell_id,
        crop_code=task.crop_code,
        target_code=task.target_code,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        assignment_type=task.assignment_type,
        deadline=task.deadline.isoformat() if task.deadline else None,
        suspected_issue=task.suspected_issue,
        created_at=task.created_at.isoformat(),
    )


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task_endpoint(
    task_id: str = Path(..., description="Task ID"),
    payload: TaskCompleteRequest | None = None,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Complete a task after verification (expert/admin only)."""
    if payload is None:
        payload = TaskCompleteRequest(task_id=task_id, verified=True)

    try:
        task = complete_task(db, task_id=task_id, user_id=user.id, verified=payload.verified)
    except TaskServiceError as exc:
        raise ApiError(400, "task_error", str(exc)) from exc
    db.commit()
    return TaskResponse(
        task_id=task.id,
        h3_cell_id=task.h3_cell_id,
        crop_code=task.crop_code,
        target_code=task.target_code,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        assignment_type=task.assignment_type,
        deadline=task.deadline.isoformat() if task.deadline else None,
        suspected_issue=task.suspected_issue,
        created_at=task.created_at.isoformat(),
    )


@router.post("/{task_id}/reassign", response_model=TaskResponse)
def reassign_task_endpoint(
    task_id: str = Path(..., description="Task ID"),
    payload: TaskReassignRequest | None = None,
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Reassign a task to a different user (admin/expert only)."""
    if payload is None:
        raise ApiError(400, "payload_required", "Reassignment payload is required")

    try:
        task = reassign_task(
            db, task_id=task_id, new_user_id=payload.new_user_id,
            reassigned_by=user.id, reason=payload.reason,
        )
    except TaskServiceError as exc:
        raise ApiError(400, "task_error", str(exc)) from exc
    db.commit()
    return TaskResponse(
        task_id=task.id,
        h3_cell_id=task.h3_cell_id,
        crop_code=task.crop_code,
        target_code=task.target_code,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        assignment_type=task.assignment_type,
        deadline=task.deadline.isoformat() if task.deadline else None,
        suspected_issue=task.suspected_issue,
        created_at=task.created_at.isoformat(),
    )


@router.get("/eligible-users")
def eligible_users_for_task(
    h3_cell_id: str = Query(..., description="H3 cell ID"),
    task_type: str = Query(
        ...,
        pattern="^(hotspot_verification|routine_scouting|recovery_inspection|expert_review)$",
    ),
    crop_code: str = Query(...),
    target_code: str = Query(...),
    required_expertise: Optional[str] = Query(default=None, description="Comma-separated expertise list"),
    max_distance_km: Optional[float] = Query(default=None, gt=0, le=100),
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Find eligible users for a task."""
    expertise_list = (
        [e.strip() for e in required_expertise.split(",") if e.strip()]
        if required_expertise
        else []
    )
    eligible = find_eligible_users(
        db=db,
        h3_cell_id=h3_cell_id,
        task_type=task_type,
        required_expertise=expertise_list,
        crop_code=crop_code,
        target_code=target_code,
        max_distance_km=max_distance_km,
    )
    return {
        "cell_id": h3_cell_id,
        "eligible_users": [EligibleUserResponse(**e) for e in eligible],
        "count": len(eligible),
    }


@router.post("/expire-overdue")
def expire_overdue(
    user=Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Mark overdue tasks as EXPIRED (admin/system only)."""
    count = expire_overdue_tasks(db)
    db.commit()
    return {"expired_count": count}


__all__ = ["router"]
