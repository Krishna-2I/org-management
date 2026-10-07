import logging

from sqlalchemy import or_, select
from sqlalchemy.orm import aliased

from app.core.cache import cache_invalidate
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models.department import Department
from app.models.user import Role, User
from app.services.common import get_in_org
from app.services.permissions import assert_can_manage_user, can_view_user, scope_users
from app.utils.pagination import paginate

log = logging.getLogger("app.users")

USER_SORT = {
    "id": User.id,
    "name": User.full_name,
    "email": User.email,
    "created_at": User.created_at,
    "role": User.role,
}


def _validate_department_and_manager(db, actor: User, department_id, manager_id):
    if department_id is not None:
        department = db.scalar(
            select(Department).where(Department.id == department_id, Department.org_id == actor.org_id)
        )
        if department is None:
            raise NotFoundError("Department not found")
    if manager_id is not None:
        manager = db.scalar(select(User).where(User.id == manager_id, User.org_id == actor.org_id))
        if manager is None:
            raise NotFoundError("Manager not found")


def create_user(db, actor: User, data) -> User:
    if actor.role == Role.EMPLOYEE:
        raise ForbiddenError()

    if actor.role == Role.MANAGER:
        if data.role != Role.EMPLOYEE:
            raise ForbiddenError("Managers can only create employees")
        if data.department_id and data.department_id != actor.department_id:
            raise ForbiddenError("Managers can only add users to their own department")
        data.department_id = actor.department_id

    if db.scalar(select(User.id).where(User.email == data.email)):
        raise ConflictError("Email already registered")

    _validate_department_and_manager(db, actor, data.department_id, data.manager_id)

    user = User(
        org_id=actor.org_id,
        email=data.email,
        full_name=data.full_name,
        role=data.role,
        hashed_password=hash_password(data.password),
        department_id=data.department_id,
        manager_id=data.manager_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    cache_invalidate(f"org:{actor.org_id}:")
    log.info("user created", extra={"org_id": actor.org_id, "user_id": user.id, "role": user.role.value})
    return user


def get_user(db, actor: User, user_id: int) -> User:
    target = get_in_org(db, User, user_id, actor.org_id)
    if not can_view_user(actor, target):
        raise NotFoundError("User not found")
    return target


def list_users(db, actor: User, params, q=None, role=None, department_id=None, is_active=None):
    stmt = scope_users(select(User), actor)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
    if role:
        stmt = stmt.where(User.role == role)
    if department_id:
        stmt = stmt.where(User.department_id == department_id)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    return paginate(db, stmt, params, USER_SORT, tiebreaker=User.id)


def list_users_with_relations(db, actor: User, params):
    Manager = aliased(User)
    stmt = (
        select(
            User.id,
            User.full_name,
            User.email,
            User.role,
            User.is_active,
            Department.name.label("department_name"),
            Manager.full_name.label("manager_name"),
        )
        .outerjoin(Department, User.department_id == Department.id)
        .outerjoin(Manager, User.manager_id == Manager.id)
    )
    stmt = scope_users(stmt, actor)

    sort_columns = {"id": User.id, "name": User.full_name, "email": User.email}
    result = paginate(db, stmt, params, sort_columns, tiebreaker=User.id, scalars=False)
    result["items"] = [dict(row._mapping) for row in result["items"]]
    return result


def update_user(db, actor: User, user_id: int, data) -> User:
    target = get_in_org(db, User, user_id, actor.org_id)

    if actor.id != target.id:
        assert_can_manage_user(actor, target)

    if data.department_id is not None or data.manager_id is not None:
        _validate_department_and_manager(
            db, actor, data.department_id or target.department_id, data.manager_id or target.manager_id
        )

    for field in ("full_name", "department_id", "manager_id", "phone", "address"):
        value = getattr(data, field)
        if value is not None:
            setattr(target, field, value)

    db.commit()
    db.refresh(target)
    cache_invalidate(f"org:{actor.org_id}:")
    return target


def update_role(db, actor: User, user_id: int, new_role: Role) -> User:
    target = get_in_org(db, User, user_id, actor.org_id)

    if target.role == Role.OWNER and new_role != Role.OWNER:
        remaining_owners = db.scalar(
            select(User.id).where(User.org_id == actor.org_id, User.role == Role.OWNER, User.id != target.id)
        )
        if remaining_owners is None:
            raise BadRequestError("Cannot demote the last owner")

    target.role = new_role
    db.commit()
    db.refresh(target)
    cache_invalidate(f"org:{actor.org_id}:")
    return target


def deactivate_user(db, actor: User, user_id: int) -> User:
    target = get_in_org(db, User, user_id, actor.org_id)

    if target.id == actor.id:
        raise BadRequestError("You cannot deactivate your own account")

    assert_can_manage_user(actor, target)

    if target.role == Role.OWNER:
        remaining_owners = db.scalar(
            select(User.id).where(
                User.org_id == actor.org_id,
                User.role == Role.OWNER,
                User.id != target.id,
                User.is_active.is_(True),
            )
        )
        if remaining_owners is None:
            raise BadRequestError("Cannot deactivate the last owner")

    target.is_active = False
    db.commit()
    db.refresh(target)
    cache_invalidate(f"org:{actor.org_id}:")
    return target
