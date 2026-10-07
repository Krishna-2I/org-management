from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import Role, User
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
def overview(
    actor: User = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    db: Session = Depends(get_db),
):
    return stats_service.overview(db, actor)
