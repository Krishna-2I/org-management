import logging

from sqlalchemy import select
from sqlalchemy.orm import aliased, joinedload

from app.core.cache import cache_invalidate
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.task import Task
from app.models.user import Role, User
from app.services.common import get_in_org
from app.services.permissions import can_update_task_status, can_view_task, scope_tasks
from app.utils.pagination import paginate

log = logging.getLogger("app.tasks")

TASK_SORT = {
    "id": Task.id,
    "title": Task.title,
    "status": Task.status,
    "priority": Task.priority,
    "due_date": Task.due_date,
    "created_at": Task.created_at,
}


def create_task(db, actor: User, data) -> Task:
    if actor.role == Role.EMPLOYEE:
        raise ForbiddenError()

    if data.assignee_id is not None:
        assignee = db.scalar(select(User).where(User.id == data.assignee_id, User.org_id == actor.org_id))
        if assignee is None:
            raise NotFoundError("Assignee not found")
        if actor.role == Role.MANAGER and assignee.department_id != actor.department_id:
            raise ForbiddenError("Managers can only assign tasks within their own department")

    task = Task(
        org_id=actor.org_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        assignee_id=data.assignee_id,
        created_by_id=actor.id,
        due_date=data.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    cache_invalidate(f"org:{actor.org_id}:")
    log.info("task created", extra={"org_id": actor.org_id, "task_id": task.id})
    return task


def get_task(db, actor: User, task_id: int) -> Task:
    task = get_in_org(db, Task, task_id, actor.org_id)
    if not can_view_task(actor, task):
        raise NotFoundError("Task not found")
    return task


def list_tasks(db, actor: User, params, status=None, priority=None, assignee_id=None):
    stmt = select(Task).options(joinedload(Task.assignee), joinedload(Task.created_by))
    stmt = scope_tasks(stmt, actor)
    if status:
        stmt = stmt.where(Task.status == status)
    if priority:
        stmt = stmt.where(Task.priority == priority)
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    return paginate(db, stmt, params, TASK_SORT, tiebreaker=Task.id)


def list_tasks_with_names(db, actor: User, params):
    Assignee = aliased(User)
    Creator = aliased(User)
    stmt = (
        select(
            Task.id,
            Task.title,
            Task.status,
            Task.priority,
            Task.due_date,
            Assignee.full_name.label("assignee_name"),
            Creator.full_name.label("created_by_name"),
        )
        .outerjoin(Assignee, Task.assignee_id == Assignee.id)
        .outerjoin(Creator, Task.created_by_id == Creator.id)
    )
    stmt = scope_tasks(stmt, actor)
    result = paginate(db, stmt, params, TASK_SORT, tiebreaker=Task.id, scalars=False)
    result["items"] = [dict(row._mapping) for row in result["items"]]
    return result


def update_task(db, actor: User, task_id: int, data) -> Task:
    task = get_task(db, actor, task_id)
    if actor.role == Role.EMPLOYEE:
        raise ForbiddenError()

    if data.assignee_id is not None:
        assignee = db.scalar(select(User).where(User.id == data.assignee_id, User.org_id == actor.org_id))
        if assignee is None:
            raise NotFoundError("Assignee not found")
        if actor.role == Role.MANAGER and assignee.department_id != actor.department_id:
            raise ForbiddenError()

    for field in ("title", "description", "priority", "assignee_id", "due_date"):
        value = getattr(data, field)
        if value is not None:
            setattr(task, field, value)

    db.commit()
    db.refresh(task)
    cache_invalidate(f"org:{actor.org_id}:")
    return task


def update_task_status(db, actor: User, task_id: int, new_status) -> Task:
    task = get_task(db, actor, task_id)
    if not can_update_task_status(actor, task):
        raise ForbiddenError()

    task.status = new_status
    db.commit()
    db.refresh(task)
    cache_invalidate(f"org:{actor.org_id}:")
    return task
