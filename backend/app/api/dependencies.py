import hmac
from dataclasses import dataclass
from datetime import timezone

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import add_audit, ensure_utc, hash_value, utc_now, validate_csrf
from app.models import ServerSession, User


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: ServerSession
    csrf_token: str


def get_auth_context(
    request: Request,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=get_settings().session_cookie_name),
) -> AuthContext:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    session = db.scalar(
        select(ServerSession).where(
            ServerSession.session_token_hash == hash_value(session_token),
            ServerSession.is_revoked.is_(False),
            ServerSession.revoked_at.is_(None),
        )
    )
    now = utc_now()
    if session is None or ensure_utc(session.expires_at) <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    user = db.get(User, session.user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    csrf_token = request.app.state.csrf_token(session.id)
    if not hmac.compare_digest(hash_value(csrf_token), session.csrf_token_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")

    # Update session last_seen_at timestamp
    session.last_seen_at = now
    db.add(session)
    db.commit()

    return AuthContext(user=user, session=session, csrf_token=csrf_token)


def require_csrf(
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> AuthContext:
    origin = request.headers.get("origin")
    allowed_origins = get_settings().cors_origins
    if origin and origin not in allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request origin is not allowed.")
    if not validate_csrf(context.session, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
    return context


def record_denied_access(request: Request, db: Session, user_id: str) -> None:
    add_audit(db, "authorization_denied", "denied", user_id, getattr(request.state, "correlation_id", None))
    db.commit()


def require_admin(
    request: Request,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> AuthContext:
    if context.user.role != "admin":
        record_denied_access(request, db, context.user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required.",
        )
    return context
