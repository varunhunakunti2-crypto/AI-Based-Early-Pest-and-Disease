"""Uber-style intelligent task distribution system.

Distributes agricultural inspection work to farmers, field agents, and
agricultural experts based on geographic proximity, availability, expertise,
and workload.

Task lifecycle:
CREATED -> AVAILABLE -> ASSIGNED -> ACCEPTED -> IN_PROGRESS ->
SUBMITTED -> UNDER_REVIEW -> VERIFIED -> COMPLETED

Terminal states: REJECTED, CANCELLED, EXPIRED, REASSIGNED
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.h3_config import default_resolution
from app.db.models import (
    FieldAgentProfile,
    InspectionTask,
    TaskAssignment,
    TaskStatusHistory,
    User,
    UserTaskAvailability,
    WeatherCellRecord,
)
from app.geo import great_circle_distance_m, h3_get_resolution, k_ring


# Task status constants
STATUS_CREATED = "CREATED"
STATUS_AVAILABLE = "AVAILABLE"
STATUS_ASSIGNED = "ASSIGNED"
STATUS_ACCEPTED = "ACCEPTED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_SUBMITTED = "SUBMITTED"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"
STATUS_VERIFIED = "VERIFIED"
STATUS_COMPLETED = "COMPLETED"
STATUS_REJECTED = "REJECTED"
STATUS_CANCELLED = "CANCELLED"
STATUS_EXPIRED = "EXPIRED"
STATUS_REASSIGNED = "REASSIGNED"

ACTIVE_STATUSES = {
    STATUS_AVAILABLE, STATUS_ASSIGNED, STATUS_ACCEPTED,
    STATUS_IN_PROGRESS, STATUS_SUBMITTED, STATUS_UNDER_REVIEW,
}

TERMINAL_STATUSES = {
    STATUS_COMPLETED, STATUS_REJECTED, STATUS_CANCELLED,
    STATUS_EXPIRED, STATUS_REASSIGNED,
}

# Priority-based automatic assignment rules
PRIORITY_AUTO_ASSIGN = {
    "urgent": True,
    "high": True,
    "moderate": False,
    "low": False,
}

# Default task expiration hours by priority
DEFAULT_EXPIRATION_HOURS = {
    "urgent": 4,
    "high": 24,
    "moderate": 72,
    "low": 168,
}


class TaskServiceError(ValueError):
    """Raised for task distribution business logic errors."""


def _record_status_change(
    db: Session,
    task: InspectionTask,
    from_status: Optional[str],
    to_status: str,
    changed_by: str,
    reason: Optional[str] = None,
) -> None:
    """Record a task status change in history."""
    history = TaskStatusHistory(
        task_id=task.id,
        from_status=from_status,
        to_status=to_status,
        changed_by=changed_by,
        reason=reason,
        is_demo=task.is_demo,
    )
    db.add(history)
    task.updated_at = datetime.now(timezone.utc)


def create_inspection_task(
    db: Session,
    h3_cell_id: str,
    crop_code: str,
    target_code: str,
    task_type: str,
    priority: str = "moderate",
    created_by: str = "system",
    deadline_hours: Optional[int] = None,
    suspected_issue: Optional[str] = None,
    crop_growth_stage: Optional[str] = None,
    inspection_instructions: Optional[str] = None,
    max_distance_km: Optional[float] = None,
    required_expertise: Optional[list] = None,
    assignment_type: str = "automatic",
    is_demo: bool = False,
) -> InspectionTask:
    """Create a new inspection task.

    Tasks start in CREATED status and are promoted to AVAILABLE for voluntary
    acceptance or auto-assigned for urgent tasks.
    """
    if resolution := h3_get_resolution(int(h3_cell_id)):
        pass  # cell_id is valid

    resolution_int = h3_get_resolution(int(h3_cell_id))

    # Calculate deadline
    if deadline_hours is None:
        deadline_hours = DEFAULT_EXPIRATION_HOURS.get(priority, 72)
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=deadline_hours)
    expires_at = deadline + timedelta(hours=24)  # Extra buffer

    task = InspectionTask(
        h3_cell_id=h3_cell_id,
        resolution=resolution_int,
        crop_code=crop_code,
        target_code=target_code,
        task_type=task_type,
        priority=priority,
        status=STATUS_CREATED,
        assigned_to=None,
        assigned_by=created_by,
        assignment_type=assignment_type,
        deadline=deadline,
        expires_at=expires_at,
        suspected_issue=suspected_issue,
        crop_growth_stage=crop_growth_stage,
        inspection_instructions=inspection_instructions,
        max_distance_km=max_distance_km,
        required_expertise=required_expertise or [],
        created_by=created_by,
        is_demo=is_demo,
    )
    db.add(task)
    db.flush()

    _record_status_change(
        db, task, None, STATUS_CREATED, created_by,
        reason=f"Task created: {task_type} for {target_code}",
    )

    # Auto-assign urgent/high priority tasks
    if PRIORITY_AUTO_ASSIGN.get(priority, False):
        _auto_assign_task(db, task, created_by)

    return task


def promote_to_available(db: Session, task: InspectionTask) -> None:
    """Promote a CREATED task to AVAILABLE for voluntary acceptance."""
    if task.status != STATUS_CREATED:
        raise TaskServiceError(f"Task {task.id} is not in CREATED status")

    task.status = STATUS_AVAILABLE
    _record_status_change(
        db, task, STATUS_CREATED, STATUS_AVAILABLE, task.created_by,
        reason="Task promoted to available for voluntary acceptance",
    )


def find_eligible_users(
    db: Session,
    h3_cell_id: str,
    task_type: str,
    required_expertise: list,
    crop_code: str,
    target_code: str,
    max_distance_km: Optional[float] = None,
    exclude_user_ids: Optional[list] = None,
) -> list[dict]:
    """Find eligible users for a task based on location, expertise, availability."""
    if max_distance_km is None:
        max_distance_km = 15.0

    exclude_user_ids = exclude_user_ids or []

    # Get the cell center for distance calculation
    from app.geo import h3_to_center
    cell_lat, cell_lng = h3_to_center(int(h3_cell_id))

    # Find field agents with profiles
    agent_query = select(FieldAgentProfile).where(
        FieldAgentProfile.is_available.is_(True),
    )
    agents = db.scalars(agent_query).all()

    eligible = []
    for agent in agents:
        if agent.user_id in exclude_user_ids:
            continue

        # Check workload
        if agent.current_workload >= agent.max_concurrent_tasks:
            continue

        # Check expertise
        agent_expertise = set(agent.expertise_areas or [])
        agent_crops = set(agent.crop_experience or [])
        if required_expertise and not agent_expertise.intersection(set(required_expertise)):
            continue
        if crop_code and agent_crops and crop_code not in agent_crops:
            continue

        # Check distance if agent has location
        if agent.current_lat is not None and agent.current_lng is not None:
            dist_km = great_circle_distance_m(
                cell_lat, cell_lng, float(agent.current_lat), float(agent.current_lng)
            ) / 1000.0
            if dist_km > max_distance_km:
                continue
        else:
            dist_km = None

        # Check availability windows
        avail_query = select(UserTaskAvailability).where(
            UserTaskAvailability.user_id == agent.user_id,
            UserTaskAvailability.is_active.is_(True),
            UserTaskAvailability.available_from <= datetime.now(timezone.utc),
            UserTaskAvailability.available_to >= datetime.now(timezone.utc),
        )
        availability = db.scalars(avail_query).all()

        eligible.append({
            "user_id": agent.user_id,
            "distance_km": round(dist_km, 2) if dist_km else None,
            "current_workload": agent.current_workload,
            "max_concurrent_tasks": agent.max_concurrent_tasks,
            "completion_rate": float(agent.completion_rate) if agent.completion_rate else 0.0,
            "expertise_areas": agent.expertise_areas,
            "crop_experience": agent.crop_experience,
            "has_availability": len(availability) > 0,
            "is_available": agent.is_available,
        })

    # Sort by distance (closest first), then by completion rate
    eligible.sort(key=lambda x: (x["distance_km"] or 999, -x["completion_rate"]))
    return eligible


def _auto_assign_task(db: Session, task: InspectionTask, assigned_by: str) -> None:
    """Automatically assign a task to the best eligible user."""
    eligible = find_eligible_users(
        db=db,
        h3_cell_id=task.h3_cell_id,
        task_type=task.task_type,
        required_expertise=task.required_expertise or [],
        crop_code=task.crop_code,
        target_code=task.target_code,
        max_distance_km=task.max_distance_km,
    )

    if not eligible:
        # No eligible users; task stays in CREATED or AVAILABLE
        task.status = STATUS_AVAILABLE
        _record_status_change(
            db, task, STATUS_CREATED, STATUS_AVAILABLE, assigned_by,
            reason="No eligible agents; task available for voluntary acceptance",
        )
        return

    best = eligible[0]
    user_id = best["user_id"]
    distance_km = best["distance_km"]

    # Assign the task
    task.status = STATUS_ASSIGNED
    task.assigned_to = user_id
    task.assigned_by = assigned_by

    # Update agent workload
    agent = db.scalar(select(FieldAgentProfile).where(FieldAgentProfile.user_id == user_id))
    if agent:
        agent.current_workload += 1

    _record_status_change(
        db, task, STATUS_CREATED, STATUS_ASSIGNED, assigned_by,
        reason=f"Auto-assigned to {user_id} (distance: {distance_km}km)",
    )

    # Record assignment
    assignment = TaskAssignment(
        task_id=task.id,
        user_id=user_id,
        assigned_at=datetime.now(timezone.utc),
        assigned_by=assigned_by,
        assignment_type="automatic",
        distance_km=distance_km,
        is_demo=task.is_demo,
    )
    db.add(assignment)
    db.flush()


def accept_task(
    db: Session,
    task_id: str,
    user_id: str,
) -> InspectionTask:
    """Accept an available task (voluntary acceptance)."""
    task = db.get(InspectionTask, task_id)
    if task is None:
        raise TaskServiceError(f"Task {task_id} not found")

    if task.status != STATUS_AVAILABLE:
        raise TaskServiceError(f"Task {task_id} is not AVAILABLE (status: {task.status})")

    # Check user eligibility
    eligible = find_eligible_users(
        db=db,
        h3_cell_id=task.h3_cell_id,
        task_type=task.task_type,
        required_expertise=task.required_expertise or [],
        crop_code=task.crop_code,
        target_code=task.target_code,
        max_distance_km=task.max_distance_km,
        exclude_user_ids=[],
    )

    eligible_ids = [e["user_id"] for e in eligible]
    if user_id not in eligible_ids:
        raise TaskServiceError(f"User {user_id} is not eligible for task {task_id}")

    # Check if already assigned to someone
    if task.assigned_to and task.assigned_to != user_id:
        raise TaskServiceError(f"Task {task_id} is already assigned")

    from app.geo import h3_to_center
    cell_lat, cell_lng = h3_to_center(int(task.h3_cell_id))

    # Calculate distance for this user
    agent = db.scalar(select(FieldAgentProfile).where(FieldAgentProfile.user_id == user_id))
    distance_km = None
    if agent and agent.current_lat is not None and agent.current_lng is not None:
        distance_km = great_circle_distance_m(
            cell_lat, cell_lng, float(agent.current_lat), float(agent.current_lng)
        ) / 1000.0

    # Accept the task
    task.status = STATUS_ACCEPTED
    task.assigned_to = user_id
    task.assigned_by = user_id  # Self-assigned via voluntary acceptance
    task.assignment_type = "voluntary"

    # Update agent workload
    if agent:
        agent.current_workload += 1

    _record_status_change(
        db, task, STATUS_AVAILABLE, STATUS_ACCEPTED, user_id,
        reason=f"Task accepted voluntarily (distance: {distance_km}km)",
    )

    # Record assignment
    assignment = TaskAssignment(
        task_id=task.id,
        user_id=user_id,
        assigned_at=datetime.now(timezone.utc),
        assigned_by=user_id,
        assignment_type="voluntary",
        distance_km=distance_km,
        is_demo=task.is_demo,
    )
    db.add(assignment)
    db.flush()

    return task


def decline_task(
    db: Session,
    task_id: str,
    user_id: str,
) -> dict:
    """Decline an available task."""
    task = db.get(InspectionTask, task_id)
    if task is None:
        raise TaskServiceError(f"Task {task_id} not found")

    if task.status != STATUS_AVAILABLE:
        raise TaskServiceError(f"Task {task_id} is not AVAILABLE")

    _record_status_change(
        db, task, STATUS_AVAILABLE, STATUS_AVAILABLE, user_id,
        reason="Task declined",
    )

    return {"task_id": task_id, "status": task.status, "declined_by": user_id}


def start_task(
    db: Session,
    task_id: str,
    user_id: str,
) -> InspectionTask:
    """Start an accepted task (move to IN_PROGRESS)."""
    task = db.get(InspectionTask, task_id)
    if task is None:
        raise TaskServiceError(f"Task {task_id} not found")

    if task.status != STATUS_ACCEPTED:
        raise TaskServiceError(f"Task {task_id} is not ACCEPTED (status: {task.status})")

    if task.assigned_to != user_id:
        raise TaskServiceError(f"User {user_id} is not assigned to task {task_id}")

    task.status = STATUS_IN_PROGRESS
    _record_status_change(
        db, task, STATUS_ACCEPTED, STATUS_IN_PROGRESS, user_id,
        reason="Task started",
    )
    db.flush()
    return task


def submit_task(
    db: Session,
    task_id: str,
    user_id: str,
) -> InspectionTask:
    """Submit a completed task for review (move to SUBMITTED)."""
    task = db.get(InspectionTask, task_id)
    if task is None:
        raise TaskServiceError(f"Task {task_id} not found")

    if task.status != STATUS_IN_PROGRESS:
        raise TaskServiceError(f"Task {task_id} is not IN_PROGRESS")

    if task.assigned_to != user_id:
        raise TaskServiceError(f"User {user_id} is not assigned to task {task_id}")

    task.status = STATUS_SUBMITTED
    _record_status_change(
        db, task, STATUS_IN_PROGRESS, STATUS_SUBMITTED, user_id,
        reason="Task submitted for review",
    )
    db.flush()
    return task


def complete_task(
    db: Session,
    task_id: str,
    user_id: str,
    verified: bool = True,
) -> InspectionTask:
    """Complete a task after verification."""
    task = db.get(InspectionTask, task_id)
    if task is None:
        raise TaskServiceError(f"Task {task_id} not found")

    if task.status not in (STATUS_SUBMITTED, STATUS_UNDER_REVIEW):
        raise TaskServiceError(f"Task {task_id} cannot be completed from {task.status}")

    task.status = STATUS_COMPLETED
    _record_status_change(
        db, task, task.status, STATUS_COMPLETED, user_id,
        reason="Task completed and verified" if verified else "Task completed",
    )

    # Decrease agent workload
    agent = db.scalar(select(FieldAgentProfile).where(FieldAgentProfile.user_id == task.assigned_to))
    if agent and agent.current_workload > 0:
        agent.current_workload -= 1

    db.flush()
    return task


def reassign_task(
    db: Session,
    task_id: str,
    new_user_id: str,
    reassigned_by: str,
    reason: Optional[str] = None,
) -> InspectionTask:
    """Reassign a task to a different user."""
    task = db.get(InspectionTask, task_id)
    if task is None:
        raise TaskServiceError(f"Task {task_id} not found")

    if task.status in TERMINAL_STATUSES:
        raise TaskServiceError(f"Cannot reassign task in {task.status} status")

    old_assignee = task.assigned_to

    # Decrease old assignee workload
    if old_assignee:
        old_agent = db.scalar(select(FieldAgentProfile).where(FieldAgentProfile.user_id == old_assignee))
        if old_agent and old_agent.current_workload > 0:
            old_agent.current_workload -= 1

    task.status = STATUS_REASSIGNED
    task.assigned_to = new_user_id
    task.assigned_by = reassigned_by

    # Increase new assignee workload
    new_agent = db.scalar(select(FieldAgentProfile).where(FieldAgentProfile.user_id == new_user_id))
    if new_agent:
        new_agent.current_workload += 1

    _record_status_change(
        db, task, task.status, STATUS_REASSIGNED, reassigned_by,
        reason=reason or "Task reassigned",
    )

    # Record new assignment
    assignment = TaskAssignment(
        task_id=task.id,
        user_id=new_user_id,
        assigned_at=datetime.now(timezone.utc),
        assigned_by=reassigned_by,
        assignment_type="automatic",
        is_demo=task.is_demo,
    )
    db.add(assignment)
    db.flush()

    return task


def expire_overdue_tasks(db: Session) -> int:
    """Mark overdue tasks as EXPIRED."""
    now = datetime.now(timezone.utc)
    expired = db.scalars(
        select(InspectionTask).where(
            InspectionTask.status.in_(ACTIVE_STATUSES),
            InspectionTask.expires_at < now,
        )
    ).all()

    count = 0
    for task in expired:
        task.status = STATUS_EXPIRED
        _record_status_change(
            db, task, task.status, STATUS_EXPIRED, "system",
            reason="Task expired",
        )
        # Decrease workload
        if task.assigned_to:
            agent = db.scalar(select(FieldAgentProfile).where(FieldAgentProfile.user_id == task.assigned_to))
            if agent and agent.current_workload > 0:
                agent.current_workload -= 1
        count += 1

    return count


def get_user_tasks(
    db: Session,
    user_id: str,
    status_filter: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Get tasks assigned to a user."""
    query = select(InspectionTask).where(InspectionTask.assigned_to == user_id)
    if status_filter:
        query = query.where(InspectionTask.status == status_filter)
    query = query.order_by(InspectionTask.created_at.desc()).limit(limit)
    rows = db.scalars(query).all()
    return [
        {
            "task_id": row.id,
            "h3_cell_id": row.h3_cell_id,
            "crop_code": row.crop_code,
            "target_code": row.target_code,
            "task_type": row.task_type,
            "priority": row.priority,
            "status": row.status,
            "assignment_type": row.assignment_type,
            "deadline": row.deadline.isoformat() if row.deadline else None,
            "suspected_issue": row.suspected_issue,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def get_available_tasks(
    db: Session,
    user_id: str,
    limit: int = 50,
) -> list[dict]:
    """Get available tasks that a user can voluntarily accept."""
    # Find tasks in AVAILABLE status
    query = select(InspectionTask).where(
        InspectionTask.status == STATUS_AVAILABLE,
        InspectionTask.expires_at > datetime.now(timezone.utc),
    ).order_by(InspectionTask.priority, InspectionTask.created_at.desc()).limit(limit * 3)

    rows = db.scalars(query).all()
    available = []

    for row in rows:
        # Check user eligibility
        eligible = find_eligible_users(
            db=db,
            h3_cell_id=row.h3_cell_id,
            task_type=row.task_type,
            required_expertise=row.required_expertise or [],
            crop_code=row.crop_code,
            target_code=row.target_code,
            max_distance_km=row.max_distance_km,
            exclude_user_ids=[],
        )
        eligible_ids = [e["user_id"] for e in eligible]
        if user_id in eligible_ids:
            user_info = next(e for e in eligible if e["user_id"] == user_id)
            available.append({
                "task_id": row.id,
                "h3_cell_id": row.h3_cell_id,
                "crop_code": row.crop_code,
                "target_code": row.target_code,
                "task_type": row.task_type,
                "priority": row.priority,
                "deadline": row.deadline.isoformat() if row.deadline else None,
                "suspected_issue": row.suspected_issue,
                "distance_km": user_info["distance_km"],
                "created_at": row.created_at.isoformat(),
            })

    available.sort(key=lambda x: (x["priority"] != "urgent", x["priority"] != "high", x["distance_km"] or 999))
    return available[:limit]


__all__ = [
    "STATUS_CREATED", "STATUS_AVAILABLE", "STATUS_ASSIGNED", "STATUS_ACCEPTED",
    "STATUS_IN_PROGRESS", "STATUS_SUBMITTED", "STATUS_UNDER_REVIEW", "STATUS_VERIFIED",
    "STATUS_COMPLETED", "STATUS_REJECTED", "STATUS_CANCELLED", "STATUS_EXPIRED",
    "STATUS_REASSIGNED",
    "TaskServiceError",
    "create_inspection_task",
    "promote_to_available",
    "find_eligible_users",
    "accept_task",
    "decline_task",
    "start_task",
    "submit_task",
    "complete_task",
    "reassign_task",
    "expire_overdue_tasks",
    "get_user_tasks",
    "get_available_tasks",
]
