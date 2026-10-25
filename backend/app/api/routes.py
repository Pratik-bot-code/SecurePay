from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, get_auth_context, require_csrf
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    add_audit,
    csrf_token_for,
    hash_password,
    increment_rate_limit,
    new_session,
    utc_now,
    verify_password,
)
from app.models import (
    DemoAccount,
    Notification,
    ServerSession,
    User,
)
from app.schemas.api import (
    AccountResponse,
    ChangePasswordRequest,
    DashboardResponse,
    LoginRequest,
    NotificationReadRequest,
    NotificationResponse,
    PreferencesUpdateRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    SessionResponse,
    UserResponse,
)
from app.services.serialization import notification_response, user_response

router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["authentication"])


def _aware(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 60 * 60,
        path="/",
    )


def _session_response(session: ServerSession, current_session_id: str) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        created_at=session.created_at,
        last_seen_at=session.last_seen_at,
        expires_at=session.expires_at,
        current=session.id == current_session_id,
        label="This device" if session.id == current_session_id else "Other browser session",
    )


@auth_router.post("/register", status_code=201)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    host = request.client.host if request.client else "unknown"
    if not increment_rate_limit(db, "register", host, settings.rate_limit_register_per_minute):
        add_audit(db, "registration", "rate_limited", correlation_id=getattr(request.state, "correlation_id", None))
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again shortly.")
    db.commit()
    exists = db.scalar(select(User.id).where(User.demo_handle == body.demo_handle))
    if exists:
        add_audit(db, "registration", "denied", correlation_id=getattr(request.state, "correlation_id", None))
        db.commit()
        raise HTTPException(status_code=400, detail="Unable to create this account. Check the details or choose another Profile ID.")
    try:
        user = User(
            demo_handle=body.demo_handle,
            display_name=body.display_name,
            password_hash=hash_password(body.password),
        )
        db.add(user)
        db.flush()
        account = DemoAccount(user_id=user.id, label="SecurePay account", account_type="user", balance_paise=0)
        db.add(account)
        db.flush()
        db.add_all(
            [
                Notification(user_id=user.id, title="Your SecurePay account is ready", body="Connect an approved payment provider to access payment features.", icon="sparkles"),
                Notification(user_id=user.id, title="Keep your account secure", body="Never enter a PIN, OTP, card number, or banking password unless an approved provider securely requests it.", icon="shield"),
            ]
        )
        add_audit(db, "registration", "success", user.id, getattr(request.state, "correlation_id", None))
        db.commit()
        return {"user": user_response(user)}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unable to create this account. Check the details or choose another Profile ID.")


@auth_router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    host = request.client.host if request.client else "unknown"
    allowed = increment_rate_limit(db, "login-ip", host, settings.rate_limit_login_per_minute * 3)
    allowed = increment_rate_limit(db, "login-handle", f"{host}:{body.demo_handle}", settings.rate_limit_login_per_minute) and allowed
    if not allowed:
        add_audit(db, "login", "rate_limited", correlation_id=getattr(request.state, "correlation_id", None))
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again shortly.")
    db.commit()
    user = db.scalar(select(User).where(User.demo_handle == body.demo_handle, User.is_directory.is_(False)))
    valid = user is not None and user.status == "active" and verify_password(body.password, user.password_hash)
    if not valid:
        add_audit(db, "login", "denied", user.id if user else None, getattr(request.state, "correlation_id", None))
        if user is not None and user.security_alerts:
            db.add(Notification(
                user_id=user.id,
                title="Unsuccessful sign-in attempt",
                body="A sign-in to your SecurePay account failed. Review active sessions if this was not you.",
                icon="shield",
            ))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid Profile ID or password.")
    session, token, csrf = new_session(db, user.id)
    add_audit(db, "login", "success", user.id, getattr(request.state, "correlation_id", None))
    db.commit()
    _set_session_cookie(response, token)
    return {"user": user_response(user), "csrf_token": csrf}


@auth_router.get("/session")
def read_session(context: AuthContext = Depends(get_auth_context)):
    return {"user": user_response(context.user), "csrf_token": context.csrf_token}


@auth_router.post("/logout", status_code=204)
def logout(
    request: Request,
    context: AuthContext = Depends(require_csrf),
    response: Response = None,
    db: Session = Depends(get_db),
):
    context.session.is_revoked = True
    context.session.revoked_at = utc_now()
    add_audit(db, "logout", "success", context.user.id, getattr(request.state, "correlation_id", None))
    db.commit()
    if response is not None:
        response.delete_cookie(
            key=get_settings().session_cookie_name,
            path="/",
            secure=get_settings().session_cookie_secure,
            httponly=True,
            samesite="lax",
        )
    return None


@auth_router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    sessions = db.scalars(
        select(ServerSession)
        .where(
            ServerSession.user_id == context.user.id,
            ServerSession.is_revoked.is_(False),
            ServerSession.revoked_at.is_(None),
            ServerSession.expires_at > utc_now(),
        )
        .order_by(ServerSession.created_at.desc())
    ).all()
    return [_session_response(item, context.session.id) for item in sessions]


@auth_router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(
    request: Request,
    session_id: str,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    if session_id == context.session.id:
        raise HTTPException(status_code=422, detail="Use sign out to end this session.")
    session = db.scalar(
        select(ServerSession).where(
            ServerSession.id == session_id,
            ServerSession.user_id == context.user.id,
            ServerSession.is_revoked.is_(False),
        )
    )
    if session is None:
        add_audit(db, "session_revocation", "denied", context.user.id, getattr(request.state, "correlation_id", None))
        db.commit()
        raise HTTPException(status_code=404, detail="Session was not found.")
    session.is_revoked = True
    session.revoked_at = utc_now()
    add_audit(db, "session_revocation", "success", context.user.id, getattr(request.state, "correlation_id", None))
    db.commit()
    return Response(status_code=204)


@auth_router.put("/password")
def change_password(
    request: Request,
    body: ChangePasswordRequest,
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, context.user.password_hash):
        add_audit(db, "password_change", "denied", context.user.id, getattr(request.state, "correlation_id", None))
        db.commit()
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    context.user.password_hash = hash_password(body.new_password)
    sessions = db.scalars(
        select(ServerSession).where(
            ServerSession.user_id == context.user.id,
            ServerSession.id != context.session.id,
            ServerSession.is_revoked.is_(False),
        )
    ).all()
    for item in sessions:
        item.is_revoked = True
        item.revoked_at = utc_now()
    context.session.is_revoked = True
    context.session.revoked_at = utc_now()
    session, token, csrf = new_session(db, context.user.id)
    add_audit(db, "password_change", "success", context.user.id, getattr(request.state, "correlation_id", None))
    db.commit()
    _set_session_cookie(response, token)
    return {"changed": True, "revoked_other_sessions": len(sessions), "csrf_token": csrf, "session_id": session.id}


@auth_router.post("/recovery")
def request_recovery(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    host = request.client.host if request.client else "unknown"
    if not increment_rate_limit(db, "recovery-host", host, settings.rate_limit_register_per_minute):
        add_audit(
            db,
            "password_recovery_request",
            "rate_limited",
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        db.commit()
        raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")
    add_audit(
        db,
        "password_recovery_request",
        "unavailable",
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    raise HTTPException(
        status_code=503,
        detail="Account recovery is unavailable because no verified contact method or recovery provider is configured.",
    )


router.include_router(auth_router)


@router.get("/health")
def health():
    return {"status": "ok", "payments_available": False}


@router.get("/profile", response_model=UserResponse)
def get_profile(context: AuthContext = Depends(get_auth_context)):
    return user_response(context.user)


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    request: Request,
    body: ProfileUpdateRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    conflict = db.scalar(
        select(User.id).where(User.demo_handle == body.demo_handle, User.id != context.user.id)
    )
    if conflict:
        raise HTTPException(status_code=409, detail="That Profile ID is unavailable.")
    context.user.display_name = body.display_name
    context.user.demo_handle = body.demo_handle
    add_audit(db, "profile_update", "success", context.user.id, getattr(request.state, "correlation_id", None))
    db.commit()
    return user_response(context.user)


@router.get("/preferences")
def get_preferences(context: AuthContext = Depends(get_auth_context)):
    return {
        "biometric_preference": context.user.biometric_preference,
        "security_alerts": context.user.security_alerts,
        "two_factor_available": False,
    }


@router.put("/preferences")
def update_preferences(
    body: PreferencesUpdateRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    context.user.biometric_preference = body.biometric_preference
    context.user.security_alerts = body.security_alerts
    db.commit()
    return {
        "biometric_preference": context.user.biometric_preference,
        "security_alerts": context.user.security_alerts,
        "two_factor_available": False,
    }


@router.get("/directory")
def list_payment_recipients(_context: AuthContext = Depends(get_auth_context)):
    return []


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    unread = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == context.user.id,
            Notification.read_at.is_(None),
        )
    ) or 0
    return DashboardResponse(
        user=user_response(context.user),
        account=AccountResponse(balance_paise=0),
        monthly_spend_paise=0,
        total_received_paise=0,
        total_sent_paise=0,
        transaction_count=0,
        recent_transactions=[],
        notifications_unread=unread,
    )


@router.get("/transactions")
def list_transactions(
    search: str = Query(default="", max_length=80),
    direction: str = Query(default="all", pattern="^(all|sent|received)$"),
    period: str = Query(default="all", pattern="^(all|month|year)$"),
    _context: AuthContext = Depends(get_auth_context),
):
    return []


@router.get("/transactions/{reference}")
def get_transaction(
    reference: str,
    _context: AuthContext = Depends(get_auth_context),
):
    raise HTTPException(status_code=404, detail="No provider transaction was found.")


@router.post("/transfers")
def send_transfer(
    _context: AuthContext = Depends(require_csrf),
):
    raise HTTPException(
        status_code=503,
        detail="Transfers are unavailable until an approved payment provider is connected.",
    )


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    items = db.scalars(
        select(Notification)
        .where(Notification.user_id == context.user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    ).all()
    return [notification_response(item) for item in items]


@router.patch("/notifications/{notification_id}")
def set_notification_read(
    notification_id: str,
    body: NotificationReadRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    item = db.scalar(select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == context.user.id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Notification was not found.")
    item.read_at = utc_now() if body.read else None
    db.commit()
    return notification_response(item)


@router.post("/notifications/read-all", status_code=204)
def mark_notifications_read(context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db)):
    notifications = db.scalars(
        select(Notification).where(
            Notification.user_id == context.user.id,
            Notification.read_at.is_(None),
        )
    ).all()
    now = utc_now()
    for item in notifications:
        item.read_at = now
    db.commit()
    return Response(status_code=204)
