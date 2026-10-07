from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.common import Page
from app.schemas.user import RoleUpdate, UserCreate, UserDetailRead, UserRead, UserUpdate, UserWithRelations
from app.services import user_service
from app.utils.pagination import ListParams

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    data: UserCreate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.create_user(db, actor, data)


@router.get("", response_model=Page[UserRead])
def list_users(
    q: str | None = None,
    role: Role | None = None,
    department_id: int | None = None,
    is_active: bool | None = None,
    params: ListParams = Depends(),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.list_users(db, actor, params, q=q, role=role, department_id=department_id, is_active=is_active)


@router.get("/with-relations", response_model=Page[UserWithRelations])
def list_users_with_relations(
    params: ListParams = Depends(),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.list_users_with_relations(db, actor, params)


@router.get("/{user_id}", response_model=UserDetailRead)
def get_user(
    user_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.get_user(db, actor, user_id)


@router.patch("/{user_id}", response_model=UserDetailRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.update_user(db, actor, user_id, data)


@router.patch("/{user_id}/role", response_model=UserRead, dependencies=[Depends(require_roles(Role.OWNER))])
def update_role(
    user_id: int,
    data: RoleUpdate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.update_role(db, actor, user_id, data.role)


@router.post("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.deactivate_user(db, actor, user_id)
