from cryptography.fernet import Fernet, MultiFernet

from app.core.config import settings


def _build_fernet() -> MultiFernet:
    keys = [k.strip() for k in settings.fernet_keys.split(",") if k.strip()]
    if not keys:
        keys = [Fernet.generate_key().decode()]
    return MultiFernet([Fernet(k) for k in keys])


_fernet = _build_fernet()


def encrypt(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()
