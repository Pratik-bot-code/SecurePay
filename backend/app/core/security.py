import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AuditEvent, RateLimitBucket, ServerSession

password_hash = PasswordHash.recommended()
security_logger = logging.getLogger("securepay.security")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    try:
        return password_hash.verify(value, hashed)
    except (ValueError, TypeError):
        return False


def new_session(db: Session, user_id: str) -> tuple[ServerSession, str, str]:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    session = ServerSession(
        user_id=user_id,
        session_token_hash=hash_value(token),
        csrf_token_hash="",
        expires_at=utc_now() + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    db.flush()
    csrf = csrf_token_for(session.id)
    session.csrf_token_hash = hash_value(csrf)
    return session, token, csrf


def csrf_token_for(session_id: str) -> str:
    secret = get_settings().session_secret.encode("utf-8")
    return hmac.new(secret, f"securepay-csrf:{session_id}".encode(), hashlib.sha256).hexdigest()


def validate_csrf(session: ServerSession, supplied: str | None) -> bool:
    if not supplied:
        return False
    expected_hash = session.csrf_token_hash
    return hmac.compare_digest(hash_value(supplied), expected_hash)


def add_audit(db: Session, event_type: str, outcome: str, user_id: str | None = None, correlation_id: str | None = None) -> None:
    db.add(AuditEvent(user_id=user_id, event_type=event_type, outcome=outcome, correlation_id=correlation_id))
    if outcome in {"denied", "rate_limited", "velocity_limited", "unavailable"}:
        security_logger.warning(
            "Security event recorded",
            extra={"event_type": event_type, "outcome": outcome, "request_id": correlation_id},
        )


def _rate_limit_key(bucket_name: str, identity: str) -> str:
    secret = get_settings().session_secret.encode("utf-8")
    return hmac.new(secret, f"{bucket_name}:{identity}".encode(), hashlib.sha256).hexdigest()


def increment_rate_limit(db: Session, bucket_name: str, identity: str, limit: int) -> bool:
    now_minute = int(utc_now().timestamp() // 60)
    key_hash = _rate_limit_key(bucket_name, identity)
    dialect = db.get_bind().dialect.name
    insert = sqlite_insert if dialect == "sqlite" else pg_insert if dialect == "postgresql" else None
    if insert is None:
        raise RuntimeError(f"Rate limiting is not configured for database dialect {dialect}.")
    statement = insert(RateLimitBucket).values(
        key_hash=key_hash,
        window_start=now_minute,
        request_count=1,
    )
    statement = statement.on_conflict_do_update(
        index_elements=["key_hash", "window_start"],
        set_={"request_count": RateLimitBucket.request_count + 1},
    )
    db.execute(statement)
    bucket = db.scalar(
        select(RateLimitBucket).where(
            RateLimitBucket.key_hash == key_hash,
            RateLimitBucket.window_start == now_minute,
        )
    )
    return bool(bucket and bucket.request_count <= limit)
