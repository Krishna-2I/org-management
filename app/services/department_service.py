import logging

from sqlalchemy import and_, func, select

from app.core.cache import cache_invalidate
from app.core.exceptions import ConflictError
from app.models.department import Department
from app.models.user import User
from app.services.common import get_in_org
from app.utils.pagination import paginate

log = logging.getLogger("app.departments")

DEPARTMENT_SORT = {"id": Department.id, "name": Department.name, "created_at": Department.created_at}


def create_department(db, actor: User, data) -> Department:
    existing = db.scalar(
        select(Department.id).where(Department.org_id == actor.org_id, Department.name == data.name)
    )
    if existing:
        raise ConflictError("Department already exists")

    department = Department(org_id=actor.org_id, name=data.name)
    db.add(department)
    db.commit()
    db.refresh(department)

    cache_invalidate(f"org:{actor.org_id}:")
    log.info("department created", extra={"org_id": actor.org_id, "department_id": department.id})
    return department


def get_department(db, actor: User, department_id: int) -> Department:
    return get_in_org(db, Department, department_id, actor.org_id)


def list_departments(db, actor: User, params):
    stmt = select(Department).where(Department.org_id == actor.org_id)
    return paginate(db, stmt, params, DEPARTMENT_SORT, tiebreaker=Department.id)


def list_departments_with_headcount(db, actor: User) -> list[dict]:
    stmt = (
        select(Department.id, Department.name, func.count(User.id).label("headcount"))
        .outerjoin(User, and_(User.department_id == Department.id, User.is_active.is_(True)))
        .where(Department.org_id == actor.org_id)
        .group_by(Department.id, Department.name)
        .order_by(Department.name)
    )
    rows = db.execute(stmt).all()
    return [{"id": r.id, "name": r.name, "headcount": r.headcount} for r in rows]


def update_department(db, actor: User, department_id: int, data) -> Department:
    department = get_department(db, actor, department_id)
    if data.name is not None:
        department.name = data.name
    db.commit()
    db.refresh(department)
    cache_invalidate(f"org:{actor.org_id}:")
    return department


def delete_department(db, actor: User, department_id: int) -> None:
    department = get_department(db, actor, department_id)
    in_use = db.scalar(select(User.id).where(User.department_id == department_id))
    if in_use:
        raise ConflictError("Department still has users assigned")
    db.delete(department)
    db.commit()
    cache_invalidate(f"org:{actor.org_id}:")
