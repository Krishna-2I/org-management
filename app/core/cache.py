import json
import logging

import redis

from app.core.config import settings

log = logging.getLogger("app.cache")

_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_timeout=0.5,
    socket_connect_timeout=0.5,
)


def cache_get(key: str):
    try:
        raw = _client.get(key)
    except redis.RedisError as exc:
        log.warning("cache unavailable", extra={"error": str(exc)})
        return None
    log.info("cache hit" if raw else "cache miss", extra={"key": key})
    return json.loads(raw) if raw else None


def cache_set(key: str, value, ttl: int | None = None) -> None:
    try:
        _client.set(key, json.dumps(value, default=str), ex=ttl or settings.cache_ttl_seconds)
    except redis.RedisError as exc:
        log.warning("cache unavailable", extra={"error": str(exc)})


def cache_invalidate(prefix: str) -> None:
    try:
        for key in _client.scan_iter(match=prefix + "*"):
            _client.delete(key)
    except redis.RedisError as exc:
        log.warning("cache unavailable", extra={"error": str(exc)})


def blacklist_jti(jti: str, ttl_seconds: int) -> None:
    try:
        _client.set(f"bl:{jti}", "1", ex=max(ttl_seconds, 1))
    except redis.RedisError as exc:
        log.warning("blacklist write failed", extra={"error": str(exc)})


def is_blacklisted(jti: str) -> bool:
    try:
        return bool(_client.exists(f"bl:{jti}"))
    except redis.RedisError:
        return False
