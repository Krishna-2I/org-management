import logging
import re
import secrets

from sqlalchemy import select

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import Role, User

log = logging.getLogger("app.org")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def _make_unique_slug(db, name: str) -> str:
    base = _slugify(name)
    slug = base
    while db.scalar(select(Organization.id).where(Organization.slug == slug)):
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


def register_organization(db, data) -> User:
    if db.scalar(select(User.id).where(User.email == data.owner_email)):
        raise ConflictError("Email already registered")

    org = Organization(name=data.org_name, slug=_make_unique_slug(db, data.org_name))
    db.add(org)
    db.flush()

    owner = User(
        org_id=org.id,
        email=data.owner_email,
        full_name=data.owner_name,
        role=Role.OWNER,
        hashed_password=hash_password(data.password),
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    log.info("organization registered", extra={"org_id": org.id, "owner_id": owner.id})
    return owner


def get_organization(db, actor: User) -> Organization:
    return db.get(Organization, actor.org_id)
