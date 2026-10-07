from sqlalchemy import func, select

from app.core.cache import cache_get, cache_set
from app.models.task import Task
from app.models.user import Role, User
from app.services.department_service import list_departments_with_headcount
from app.services.permissions import scope_tasks, scope_users


def _cache_key(actor: User) -> str:
    if actor.role == Role.OWNER:
        return f"org:{actor.org_id}:stats"
    return f"org:{actor.org_id}:dept:{actor.department_id}:stats"


def overview(db, actor: User) -> dict:
    key = _cache_key(actor)
    cached = cache_get(key)
    if cached is not None:
        return cached

    users_by_role = db.execute(
        scope_users(select(User.role, func.count(User.id)).group_by(User.role), actor)
    ).all()

    tasks_by_status = db.execute(
        scope_tasks(select(Task.status, func.count(Task.id)).group_by(Task.status), actor)
    ).all()

    headcount = list_departments_with_headcount(db, actor)
    if actor.role == Role.MANAGER:
        headcount = [d for d in headcount if d["id"] == actor.department_id]

    result = {
        "users_by_role": {role.value: count for role, count in users_by_role},
        "tasks_by_status": {status.value: count for status, count in tasks_by_status},
        "departments": headcount,
    }
    cache_set(key, result)
    return result
