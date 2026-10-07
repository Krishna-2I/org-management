from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.task import Task
from app.models.user import Role, User


def scope_users(stmt, actor: User):
    stmt = stmt.where(User.org_id == actor.org_id)
    if actor.role == Role.MANAGER:
        stmt = stmt.where(User.department_id == actor.department_id)
    elif actor.role == Role.EMPLOYEE:
        stmt = stmt.where(User.id == actor.id)
    return stmt


def can_view_user(actor: User, target: User) -> bool:
    if actor.org_id != target.org_id:
        return False
    if actor.role == Role.OWNER:
        return True
    if actor.role == Role.MANAGER:
        return target.department_id == actor.department_id
    return target.id == actor.id


def can_manage_user(actor: User, target: User) -> bool:
    if actor.org_id != target.org_id:
        return False
    if actor.role == Role.OWNER:
        return True
    if actor.role == Role.MANAGER:
        return (
            target.role == Role.EMPLOYEE
            and target.department_id is not None
            and target.department_id == actor.department_id
        )
    return False


def assert_can_manage_user(actor: User, target: User) -> None:
    if not can_view_user(actor, target):
        raise NotFoundError("User not found")
    if not can_manage_user(actor, target):
        raise ForbiddenError()


def scope_tasks(stmt, actor: User):
    stmt = stmt.where(Task.org_id == actor.org_id)
    if actor.role == Role.MANAGER:
        stmt = stmt.where(
            (Task.assignee.has(department_id=actor.department_id))
            | (Task.created_by_id == actor.id)
        )
    elif actor.role == Role.EMPLOYEE:
        stmt = stmt.where(Task.assignee_id == actor.id)
    return stmt


def can_view_task(actor: User, task: Task) -> bool:
    if actor.org_id != task.org_id:
        return False
    if actor.role == Role.OWNER:
        return True
    if actor.role == Role.MANAGER:
        return (task.assignee is not None and task.assignee.department_id == actor.department_id) or (
            task.created_by_id == actor.id
        )
    return task.assignee_id == actor.id


def can_update_task_status(actor: User, task: Task) -> bool:
    if actor.role == Role.OWNER:
        return True
    if actor.role == Role.MANAGER:
        return task.assignee is not None and task.assignee.department_id == actor.department_id
    return task.assignee_id == actor.id
