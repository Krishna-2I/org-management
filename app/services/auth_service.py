import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.cache import blacklist_jti
from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User

log = logging.getLogger("app.auth")


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def authenticate(db, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    return user


def issue_refresh_token(db, user: User, family_id: str | None = None) -> str:
    raw = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(raw),
            family_id=family_id or secrets.token_hex(16),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
        )
    )
    return raw


def login(db, email: str, password: str) -> dict:
    user = authenticate(db, email, password)
    access = create_access_token(user)
    refresh = issue_refresh_token(db, user)
    db.commit()
    log.info("user logged in", extra={"user_id": user.id, "org_id": user.org_id})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


def rotate_refresh_token(db, raw_token: str) -> dict:
    now = datetime.now(timezone.utc)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token)))
    if stored is None:
        raise UnauthorizedError("Invalid refresh token")

    if stored.revoked_at is not None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == stored.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        log.warning("refresh token reuse detected", extra={"user_id": stored.user_id})
        raise UnauthorizedError("Refresh token reuse detected, all sessions revoked")

    if now >= stored.expires_at.replace(tzinfo=timezone.utc):
        raise UnauthorizedError("Refresh token expired")

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError()

    stored.revoked_at = now
    new_raw = issue_refresh_token(db, user, family_id=stored.family_id)
    db.commit()

    return {"access_token": create_access_token(user), "refresh_token": new_raw, "token_type": "bearer"}


def logout(db, access_token: str, refresh_token: str) -> None:
    payload = decode_token(access_token)
    remaining = int(payload["exp"] - datetime.now(timezone.utc).timestamp())
    blacklist_jti(payload["jti"], remaining)

    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_token)))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


def logout_all(db, user: User, access_token: str) -> None:
    payload = decode_token(access_token)
    remaining = int(payload["exp"] - datetime.now(timezone.utc).timestamp())
    blacklist_jti(payload["jti"], remaining)

    now = datetime.now(timezone.utc)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()


def change_password(db, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.hashed_password):
        raise UnauthorizedError("Current password is incorrect")

    user.hashed_password = hash_password(new_password)
    now = datetime.now(timezone.utc)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()
