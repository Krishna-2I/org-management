from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskStatusUpdate, TaskUpdate, TaskWithNames
from app.services import task_service
from app.utils.pagination import ListParams

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=201)
def create_task(
    data: TaskCreate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.create_task(db, actor, data)


@router.get("", response_model=Page[TaskRead])
def list_tasks(
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
    params: ListParams = Depends(),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.list_tasks(db, actor, params, status=status, priority=priority, assignee_id=assignee_id)


@router.get("/with-names", response_model=Page[TaskWithNames])
def list_tasks_with_names(
    params: ListParams = Depends(),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.list_tasks_with_names(db, actor, params)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.get_task(db, actor, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    data: TaskUpdate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.update_task(db, actor, task_id, data)


@router.patch("/{task_id}/status", response_model=TaskRead)
def update_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.update_task_status(db, actor, task_id, data.status)
