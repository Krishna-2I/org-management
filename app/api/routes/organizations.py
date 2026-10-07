from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.organization import OrganizationRead, OrganizationRegister
from app.schemas.user import UserRead
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/register", response_model=UserRead, status_code=201)
def register(data: OrganizationRegister, db: Session = Depends(get_db)):
    return organization_service.register_organization(db, data)


@router.get("/me", response_model=OrganizationRead)
def get_my_organization(actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return organization_service.get_organization(db, actor)
