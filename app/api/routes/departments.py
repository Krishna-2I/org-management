from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.common import Page
from app.schemas.department import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    DepartmentWithHeadcount,
)
from app.services import department_service
from app.utils.pagination import ListParams

router = APIRouter(prefix="/departments", tags=["departments"])


@router.post("", response_model=DepartmentRead, status_code=201, dependencies=[Depends(require_roles(Role.OWNER))])
def create_department(
    data: DepartmentCreate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return department_service.create_department(db, actor, data)


@router.get("", response_model=Page[DepartmentRead])
def list_departments(
    params: ListParams = Depends(),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return department_service.list_departments(db, actor, params)


@router.get("/headcount", response_model=list[DepartmentWithHeadcount])
def headcount(
    actor: User = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    db: Session = Depends(get_db),
):
    return department_service.list_departments_with_headcount(db, actor)


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(
    department_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return department_service.get_department(db, actor, department_id)


@router.patch("/{department_id}", response_model=DepartmentRead, dependencies=[Depends(require_roles(Role.OWNER))])
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return department_service.update_department(db, actor, department_id, data)


@router.delete("/{department_id}", status_code=204, dependencies=[Depends(require_roles(Role.OWNER))])
def delete_department(
    department_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    department_service.delete_department(db, actor, department_id)
