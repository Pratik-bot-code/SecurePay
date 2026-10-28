import csv
from datetime import datetime, timedelta, timezone
import io
import math
import re
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, get_auth_context, require_admin, require_csrf
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
    AuditEvent,
    DemoAccount,
    LedgerEntry,
    LinkedBankAccount,
    Merchant,
    Notification,
    PaymentOrder,
    PaymentStatusHistory,
    ServerSession,
    Transaction,
    User,
)
from app.schemas.api import (
    AccountResponse,
    AdminAuditEventResponse,
    AdminSystemStatsResponse,
    AdminUserListItem,
    AdminUserStatusUpdate,
    BankDirectoryEntry,
    ChangePasswordRequest,
    DashboardResponse,
    LinkedBankAccountCreate,
    LinkedBankAccountResponse,
    LoginRequest,
    MerchantRegisterRequest,
    MerchantResponse,
    NotificationReadRequest,
    NotificationResponse,
    PaginatedTransactionsResponse,
    PaymentOrderCreateRequest,
    PaymentOrderCreateResponse,
    PaymentOrderResponse,
    PaymentStatusHistoryResponse,
    PaymentVerifyRequest,
    PreferencesUpdateRequest,
    ProfileUpdateRequest,
    RecipientValidateRequest,
    RecipientValidateResponse,
    RegisterRequest,
    SessionResponse,
    TransactionResponse,
    TransactionSummary,
    UserResponse,
)
from app.services.bank_directory import find_bank_by_ifsc, get_bank_directory as get_banks_directory
from app.services.payment_provider import SandboxPaymentProvider, get_payment_provider
from app.services.serialization import notification_response, transaction_response, user_response

router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["authentication"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


def sanitize_csv_cell(val) -> str:
    """
    Prevent CSV formula injection (CWE-1236) by prepending a single quote
    to strings starting with dangerous formula triggers.
    """
    if val is None:
        return ""
    val_str = str(val)
    if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val_str}"
    return val_str


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
        raise HTTPException(
            status_code=400,
            detail=f"The Profile ID '@{body.demo_handle}' is already registered. Please choose another Profile ID or sign in.",
        )
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
    response: Response,
    context: AuthContext = Depends(require_csrf),
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
    if not increment_rate_limit(db, "change-password", context.user.id, 5):
        add_audit(db, "password_change", "rate_limited", context.user.id, getattr(request.state, "correlation_id", None))
        db.commit()
        raise HTTPException(status_code=429, detail="Too many password update attempts. Please wait a moment.")

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
    return {"status": "ok", "payments_available": False, "sandbox_mode": True}


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


# ---------------------------------------------------------------------------
# Indian Bank Directory Endpoints
# ---------------------------------------------------------------------------

@router.get("/banks/directory", response_model=list[BankDirectoryEntry])
def get_bank_directory_endpoint(
    search: str = Query(default="", max_length=80),
    category: str = Query(default="all", max_length=30),
    popular_only: bool = Query(default=False),
    supported_only: bool = Query(default=False),
    _context: AuthContext = Depends(get_auth_context),
):
    """
    Verified directory of Indian public-sector, private-sector, small finance,
    payments, and regional rural banks. Allows filtering by linking capability.
    """
    return get_banks_directory(
        search=search if search.strip() else None,
        category=category if category != "all" else None,
        popular_only=popular_only,
        supported_only=supported_only,
    )


@router.get("/banks/lookup/{ifsc}")
def lookup_bank_by_ifsc(
    ifsc: str,
    _context: AuthContext = Depends(get_auth_context),
):
    """
    Look up bank institution by IFSC code prefix.
    """
    bank = find_bank_by_ifsc(ifsc)
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not recognized from IFSC code prefix.")
    return bank


# ---------------------------------------------------------------------------
# Dashboard & Financial Overviews
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    unread = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == context.user.id,
            Notification.read_at.is_(None),
        )
    ) or 0

    account = db.scalar(select(DemoAccount).where(DemoAccount.user_id == context.user.id))
    balance_paise = account.balance_paise if account else 0
    currency = account.currency if account else "INR"

    recent_txs: list[TransactionResponse] = []
    monthly_spend = 0
    total_received = 0
    total_sent = 0
    tx_count = 0

    if account:
        now = utc_now()
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        monthly_spend_val = db.scalar(
            select(func.sum(LedgerEntry.amount_paise)).where(
                LedgerEntry.account_id == account.id,
                LedgerEntry.entry_type == "debit",
                LedgerEntry.created_at >= start_of_month,
            )
        )
        monthly_spend = abs(monthly_spend_val) if monthly_spend_val else 0

        total_sent_val = db.scalar(
            select(func.sum(LedgerEntry.amount_paise)).where(
                LedgerEntry.account_id == account.id,
                LedgerEntry.entry_type == "debit",
            )
        )
        total_sent = abs(total_sent_val) if total_sent_val else 0

        total_received_val = db.scalar(
            select(func.sum(LedgerEntry.amount_paise)).where(
                LedgerEntry.account_id == account.id,
                LedgerEntry.entry_type == "credit",
            )
        )
        total_received = total_received_val if total_received_val else 0

        tx_count = db.scalar(
            select(func.count(Transaction.id)).where(
                (Transaction.sender_account_id == account.id) | (Transaction.recipient_account_id == account.id)
            )
        ) or 0

        transactions = db.scalars(
            select(Transaction)
            .where((Transaction.sender_account_id == account.id) | (Transaction.recipient_account_id == account.id))
            .order_by(Transaction.created_at.desc())
            .limit(10)
        ).all()
        recent_txs = [transaction_response(db, tx, context.user) for tx in transactions]

    return DashboardResponse(
        user=user_response(context.user),
        account=AccountResponse(balance_paise=balance_paise, currency=currency),
        monthly_spend_paise=monthly_spend,
        total_received_paise=total_received,
        total_sent_paise=total_sent,
        transaction_count=tx_count,
        recent_transactions=recent_txs,
        notifications_unread=unread,
    )


# ---------------------------------------------------------------------------
# Fintech-Grade Transaction Ledger Endpoints
# ---------------------------------------------------------------------------

@router.get("/transactions/summary", response_model=TransactionSummary)
def get_transactions_summary(
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """
    Summary cards for total credits, total debits, pending, successful, and failed counts.
    """
    account = db.scalar(select(DemoAccount).where(DemoAccount.user_id == context.user.id))
    if not account:
        return TransactionSummary()

    credits = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount_paise), 0)).where(
            LedgerEntry.account_id == account.id,
            LedgerEntry.entry_type == "credit",
        )
    ) or 0

    debits = abs(db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount_paise), 0)).where(
            LedgerEntry.account_id == account.id,
            LedgerEntry.entry_type == "debit",
        )
    ) or 0)

    total_count = db.scalar(
        select(func.count(Transaction.id)).where(
            (Transaction.sender_account_id == account.id) | (Transaction.recipient_account_id == account.id)
        )
    ) or 0

    return TransactionSummary(
        total_credits_paise=credits,
        total_debits_paise=debits,
        pending_count=0,
        successful_count=total_count,
        failed_count=0,
    )


@router.get("/transactions/export")
def export_transactions_csv(
    search: str = Query(default="", max_length=80),
    direction: str = Query(default="all", pattern="^(all|sent|received)$"),
    period: str = Query(default="all", pattern="^(all|week|month|year)$"),
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """
    CSV export with access control: authenticated user can only export their own records.
    """
    account = db.scalar(select(DemoAccount).where(DemoAccount.user_id == context.user.id))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Transaction ID",
        "Reference",
        "Date & Time (UTC)",
        "Direction",
        "Counterparty",
        "Amount (INR)",
        "Status",
        "Category",
        "Payment Method",
        "Note",
    ])

    if account:
        query = select(Transaction).where(
            (Transaction.sender_account_id == account.id) | (Transaction.recipient_account_id == account.id)
        )

        if direction == "sent":
            query = query.where(Transaction.sender_account_id == account.id)
        elif direction == "received":
            query = query.where(Transaction.recipient_account_id == account.id)

        now = utc_now()
        if period == "week":
            query = query.where(Transaction.created_at >= (now - timedelta(days=7)))
        elif period == "month":
            start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
            query = query.where(Transaction.created_at >= start_of_month)
        elif period == "year":
            start_of_year = datetime(now.year, 1, 1, tzinfo=timezone.utc)
            query = query.where(Transaction.created_at >= start_of_year)

        if search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.where(
                (func.lower(Transaction.reference).like(term))
                | (func.lower(Transaction.counterparty_label).like(term))
                | (func.lower(Transaction.counterparty_handle).like(term))
                | (func.lower(Transaction.category).like(term))
            )

        txs = db.scalars(query.order_by(Transaction.created_at.desc()).limit(5000)).all()
        for tx in txs:
            tx_resp = transaction_response(db, tx, context.user)
            dir_label = "Credit" if tx_resp.signed_amount_paise > 0 else "Debit"
            writer.writerow([
                sanitize_csv_cell(tx.id),
                sanitize_csv_cell(tx.reference),
                tx.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                dir_label,
                sanitize_csv_cell(tx_resp.name),
                f"{(abs(tx.amount_paise) / 100):.2f}",
                sanitize_csv_cell(tx_resp.status),
                sanitize_csv_cell(tx.category),
                sanitize_csv_cell(tx_resp.method),
                sanitize_csv_cell(tx.note),
            ])

    output.seek(0)
    filename = f"securepay_ledger_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache",
        },
    )


@router.get("/transactions")
def list_transactions(
    search: str = Query(default="", max_length=80),
    direction: str = Query(default="all", pattern="^(all|sent|received)$"),
    period: str = Query(default="all", pattern="^(all|week|month|year)$"),
    status: str = Query(default="all", max_length=20),
    sort: str = Query(default="date_desc", pattern="^(date_desc|date_asc|amount_desc|amount_asc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    paginated: bool = Query(default=False),
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """
    Fintech ledger endpoint supporting search, direction, date period, sorting,
    and optional paginated format with summary metrics.
    """
    account = db.scalar(select(DemoAccount).where(DemoAccount.user_id == context.user.id))
    if not account:
        if paginated:
            return PaginatedTransactionsResponse(
                transactions=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                summary=TransactionSummary(),
            )
        return []

    base_query = select(Transaction).where(
        (Transaction.sender_account_id == account.id) | (Transaction.recipient_account_id == account.id)
    )

    if direction == "sent":
        base_query = base_query.where(Transaction.sender_account_id == account.id)
    elif direction == "received":
        base_query = base_query.where(Transaction.recipient_account_id == account.id)

    now = utc_now()
    if period == "week":
        base_query = base_query.where(Transaction.created_at >= (now - timedelta(days=7)))
    elif period == "month":
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        base_query = base_query.where(Transaction.created_at >= start_of_month)
    elif period == "year":
        start_of_year = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        base_query = base_query.where(Transaction.created_at >= start_of_year)

    if search.strip():
        term = f"%{search.strip().lower()}%"
        base_query = base_query.where(
            (func.lower(Transaction.reference).like(term))
            | (func.lower(Transaction.counterparty_label).like(term))
            | (func.lower(Transaction.counterparty_handle).like(term))
            | (func.lower(Transaction.category).like(term))
        )

    # Sorting
    if sort == "date_asc":
        order_clause = Transaction.created_at.asc()
    elif sort == "amount_desc":
        order_clause = Transaction.amount_paise.desc()
    elif sort == "amount_asc":
        order_clause = Transaction.amount_paise.asc()
    else:
        order_clause = Transaction.created_at.desc()

    if paginated:
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = db.scalar(count_stmt) or 0
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 0

        offset = (page - 1) * page_size
        txs = db.scalars(base_query.order_by(order_clause).offset(offset).limit(page_size)).all()

        credits = db.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount_paise), 0)).where(
                LedgerEntry.account_id == account.id,
                LedgerEntry.entry_type == "credit",
            )
        ) or 0

        debits = abs(db.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount_paise), 0)).where(
                LedgerEntry.account_id == account.id,
                LedgerEntry.entry_type == "debit",
            )
        ) or 0)

        summary = TransactionSummary(
            total_credits_paise=credits,
            total_debits_paise=debits,
            pending_count=0,
            successful_count=total,
            failed_count=0,
        )

        return PaginatedTransactionsResponse(
            transactions=[transaction_response(db, tx, context.user) for tx in txs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            summary=summary,
        )

    # Default unpaginated list (backwards-compatible with tests)
    txs = db.scalars(base_query.order_by(order_clause).limit(100)).all()
    return [transaction_response(db, tx, context.user) for tx in txs]


@router.get("/transactions/{reference}", response_model=TransactionResponse)
def get_transaction(
    reference: str,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    account = db.scalar(select(DemoAccount).where(DemoAccount.user_id == context.user.id))
    if not account:
        raise HTTPException(status_code=404, detail="No transaction was found.")

    tx = db.scalar(
        select(Transaction).where(
            Transaction.reference == reference,
            (Transaction.sender_account_id == account.id) | (Transaction.recipient_account_id == account.id),
        )
    )
    if not tx:
        raise HTTPException(status_code=404, detail="No transaction was found.")
    return transaction_response(db, tx, context.user)


# ---------------------------------------------------------------------------
# Bank Account Linking
# ---------------------------------------------------------------------------

@router.get("/accounts/banks", response_model=list[LinkedBankAccountResponse])
def list_linked_banks(
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(LinkedBankAccount)
        .where(LinkedBankAccount.user_id == context.user.id)
        .order_by(LinkedBankAccount.is_primary.desc(), LinkedBankAccount.created_at.desc())
    ).all()


@router.post("/accounts/banks", response_model=LinkedBankAccountResponse, status_code=201)
def link_bank_account(
    body: LinkedBankAccountCreate,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    existing_count = db.scalar(
        select(func.count(LinkedBankAccount.id)).where(LinkedBankAccount.user_id == context.user.id)
    ) or 0

    # Privacy by design: NEVER store raw account number, store only masked
    masked = f"•••• •••• {body.account_number[-4:]}"

    linked = LinkedBankAccount(
        user_id=context.user.id,
        bank_name=body.bank_name.strip(),
        account_holder_name=body.account_holder_name.strip(),
        masked_account_number=masked,
        ifsc_code=body.ifsc_code.strip().upper(),
        account_type=body.account_type,
        is_primary=(existing_count == 0),
        verification_status="verified",
    )
    db.add(linked)
    db.commit()
    db.refresh(linked)

    db.add(
        Notification(
            user_id=context.user.id,
            title="Bank account linked",
            body=f"{linked.bank_name} ({linked.masked_account_number}) was successfully linked.",
            icon="shield",
        )
    )
    db.commit()
    return linked


@router.delete("/accounts/banks/{bank_id}", status_code=204)
def unlink_bank_account(
    bank_id: str,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    bank = db.scalar(
        select(LinkedBankAccount).where(
            LinkedBankAccount.id == bank_id,
            LinkedBankAccount.user_id == context.user.id,
        )
    )
    if not bank:
        raise HTTPException(status_code=404, detail="Bank account not found.")

    was_primary = bank.is_primary
    db.delete(bank)
    db.flush()

    if was_primary:
        next_account = db.scalar(
            select(LinkedBankAccount)
            .where(LinkedBankAccount.user_id == context.user.id)
            .order_by(LinkedBankAccount.created_at.desc())
        )
        if next_account:
            next_account.is_primary = True

    db.commit()
    return None


@router.post("/accounts/banks/{bank_id}/primary", response_model=LinkedBankAccountResponse)
def set_primary_bank_account(
    bank_id: str,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    bank = db.scalar(
        select(LinkedBankAccount).where(
            LinkedBankAccount.id == bank_id,
            LinkedBankAccount.user_id == context.user.id,
        )
    )
    if not bank:
        raise HTTPException(status_code=404, detail="Bank account not found.")

    all_banks = db.scalars(
        select(LinkedBankAccount).where(LinkedBankAccount.user_id == context.user.id)
    ).all()
    for b in all_banks:
        b.is_primary = (b.id == bank_id)

    db.commit()
    db.refresh(bank)
    return bank


# ---------------------------------------------------------------------------
# Merchant Profiles
# ---------------------------------------------------------------------------

@router.get("/merchant", response_model=MerchantResponse)
def get_merchant_profile(
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    merchant = db.scalar(
        select(Merchant).where(Merchant.user_id == context.user.id)
    )
    if not merchant:
        raise HTTPException(status_code=404, detail="No merchant profile found for this account.")
    return merchant


@router.post("/merchant/register", response_model=MerchantResponse, status_code=201)
def register_merchant(
    body: MerchantRegisterRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(Merchant).where(Merchant.user_id == context.user.id)
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already have an active merchant profile.")

    merchant_code = f"MERCH_{secrets.token_hex(4).upper()}"
    clean_handle = context.user.demo_handle.replace(".", "").replace("-", "").replace("_", "")[:15]
    upi_handle = f"{clean_handle}.merch@securepay"

    merchant = Merchant(
        user_id=context.user.id,
        business_name=body.business_name.strip(),
        merchant_code=merchant_code,
        category=body.category.strip(),
        upi_handle=upi_handle,
        status="active",
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)

    db.add(
        Notification(
            user_id=context.user.id,
            title="Merchant Account Activated",
            body=f"Your business '{merchant.business_name}' is ready to accept payments via UPI: {merchant.upi_handle}.",
            icon="sparkles",
        )
    )
    db.commit()
    return merchant


@router.post("/transfers")
def send_transfer(
    _context: AuthContext = Depends(require_csrf),
):
    raise HTTPException(
        status_code=503,
        detail="Transfers are unavailable until an approved payment provider is connected.",
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Recipient Verification & Payment Order Routes
# ---------------------------------------------------------------------------

@router.post("/payments/validate-recipient", response_model=RecipientValidateResponse)
def validate_recipient(
    body: RecipientValidateRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    """
    Step B — Recipient validation and resolution without exposing private data.
    Validates format on backend. If recipient is on-platform, returns verified display name.
    If external UPI or mobile, validates standard format and states verification source clearly.
    Never fabricates customer name or banking details.
    """
    if not increment_rate_limit(db, "validate-recipient", context.user.id, 30):
        add_audit(db, "recipient_validation", "rate_limited", context.user.id)
        db.commit()
        raise HTTPException(status_code=429, detail="Recipient validation rate limit exceeded. Please wait a moment.")

    raw = body.identifier.strip()
    id_type = body.identifier_type

    if id_type == "upi_id":
        # Format check: standard UPI VPA pattern: user@psp
        if not re.match(r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$", raw):
            return RecipientValidateResponse(
                valid=False,
                identifier_type="upi_id",
                normalized_identifier=raw,
                message="Invalid UPI ID format. Expected format: username@bankname (e.g. rahul@okaxis)",
            )
        normalized = raw.lower()

        # Check if recipient is a SecurePay platform account
        if normalized.endswith("@securepay"):
            handle = normalized.split("@")[0]
            target_user = db.scalar(
                select(User).where(User.demo_handle == handle, User.status == "active")
            )
            if target_user:
                return RecipientValidateResponse(
                    valid=True,
                    identifier_type="upi_id",
                    normalized_identifier=normalized,
                    display_name=target_user.display_name,
                    verified=True,
                    verification_source="platform",
                    message="Recipient verified on SecurePay platform.",
                )

        # External UPI ID in sandbox mode
        provider = get_payment_provider()
        is_sandbox = isinstance(provider, SandboxPaymentProvider)
        return RecipientValidateResponse(
            valid=True,
            identifier_type="upi_id",
            normalized_identifier=normalized,
            display_name=None,
            verified=False,
            verification_source="sandbox" if is_sandbox else "provider",
            message="SANDBOX: UPI ID format is valid. Live recipient verification requires bank provider VPA resolution API."
            if is_sandbox
            else "UPI ID format verified.",
        )

    elif id_type == "mobile":
        # Indian standard mobile number: 10 digits starting with 6-9
        cleaned = re.sub(r"[\s\-\+]", "", raw)
        if cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = cleaned[2:]
        if not re.match(r"^[6-9]\d{9}$", cleaned):
            return RecipientValidateResponse(
                valid=False,
                identifier_type="mobile",
                normalized_identifier=cleaned,
                message="Invalid Indian mobile number. Must be 10 digits starting with 6, 7, 8, or 9.",
            )
        masked = f"••••••{cleaned[-4:]}"
        provider = get_payment_provider()
        is_sandbox = isinstance(provider, SandboxPaymentProvider)
        return RecipientValidateResponse(
            valid=True,
            identifier_type="mobile",
            normalized_identifier=cleaned,
            display_name=None,
            verified=False,
            verification_source="sandbox" if is_sandbox else "provider",
            message=f"SANDBOX: Mobile number {masked} validated. Live recipient resolution requires UPI Number Directory (NPCI mapper) access."
            if is_sandbox
            else f"Mobile number {masked} validated.",
        )

    elif id_type == "handle":
        handle = raw.lower().lstrip("@")
        if not re.match(r"^[a-z0-9._-]{3,30}$", handle):
            return RecipientValidateResponse(
                valid=False,
                identifier_type="handle",
                normalized_identifier=handle,
                message="Invalid handle format. Must be 3-30 letters, numbers, periods, or hyphens.",
            )
        target_user = db.scalar(
            select(User).where(User.demo_handle == handle, User.status == "active", User.is_directory.is_(False))
        )
        if target_user and target_user.id != context.user.id:
            return RecipientValidateResponse(
                valid=True,
                identifier_type="handle",
                normalized_identifier=handle,
                display_name=target_user.display_name,
                verified=True,
                verification_source="platform",
                message="Recipient found on SecurePay.",
            )
        return RecipientValidateResponse(
            valid=False,
            identifier_type="handle",
            normalized_identifier=handle,
            message="No active user found with this handle on SecurePay.",
        )

    return RecipientValidateResponse(
        valid=False,
        identifier_type=id_type,
        normalized_identifier=raw,
        message="Unsupported identifier type.",
    )


@router.post("/payments/orders", response_model=PaymentOrderCreateResponse, status_code=201)
def create_payment_order(
    body: PaymentOrderCreateRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not increment_rate_limit(db, "payment-order-create", context.user.id, 20):
        add_audit(db, "payment_order_create", "rate_limited", context.user.id)
        db.commit()
        raise HTTPException(status_code=429, detail="Payment creation rate limit exceeded. Please wait a moment.")

    provider = get_payment_provider()
    try:
        result = provider.create_order(
            db=db,
            user=context.user,
            amount_paise=body.amount_paise,
            order_type=body.order_type,
            notes=body.notes,
            idempotency_key=idempotency_key,
            recipient_identifier=body.recipient_identifier,
            recipient_type=body.recipient_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    sandbox_sig = None
    if isinstance(provider, SandboxPaymentProvider):
        sandbox_sig = provider.generate_sandbox_signature(result.order_reference, f"pay_{result.order_reference}")

    return PaymentOrderCreateResponse(
        order_id=result.order_id,
        order_reference=result.order_reference,
        amount_paise=result.amount_paise,
        currency=result.currency,
        provider_name=result.provider_name,
        provider_order_id=result.provider_order_id,
        upi_payment_url=result.upi_payment_url,
        status=result.status,
        sandbox_mode=isinstance(provider, SandboxPaymentProvider),
        sandbox_signature=sandbox_sig,
    )


@router.get("/payments/orders/{order_reference}", response_model=PaymentOrderResponse)
def get_payment_order(
    order_reference: str,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    order = db.scalar(
        select(PaymentOrder).where(
            PaymentOrder.order_reference == order_reference,
            PaymentOrder.user_id == context.user.id,
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="Payment order not found.")
    return order


@router.get("/payments/orders/{order_reference}/history", response_model=list[PaymentStatusHistoryResponse])
def get_payment_order_history(
    order_reference: str,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    order = db.scalar(
        select(PaymentOrder).where(
            PaymentOrder.order_reference == order_reference,
            PaymentOrder.user_id == context.user.id,
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="Payment order not found.")

    history = db.scalars(
        select(PaymentStatusHistory)
        .where(PaymentStatusHistory.payment_order_id == order.id)
        .order_by(PaymentStatusHistory.created_at.asc())
    ).all()
    return history


@router.post("/payments/verify", response_model=PaymentOrderResponse)
def verify_payment(
    body: PaymentVerifyRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    provider = get_payment_provider()

    is_valid = provider.verify_payment_signature(
        order_id=body.order_reference,
        payment_id=body.payment_id,
        signature=body.signature,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature. Verification failed.")

    if isinstance(provider, SandboxPaymentProvider):
        try:
            confirmed_order = provider.confirm_payment(
                db=db,
                order_reference=body.order_reference,
                payment_id=body.payment_id,
                user=context.user,
            )
            return confirmed_order
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    order = db.scalar(
        select(PaymentOrder).where(
            PaymentOrder.order_reference == body.order_reference,
            PaymentOrder.user_id == context.user.id,
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    old_status = order.status
    order.status = "paid"
    order.provider_payment_id = body.payment_id
    order.completed_at = utc_now()
    db.add(
        PaymentStatusHistory(
            payment_order_id=order.id,
            old_status=old_status,
            new_status="paid",
            reason="Verified with provider signature",
        )
    )
    db.commit()
    db.refresh(order)
    return order


@router.post("/payments/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
    signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    sandbox_sig: str | None = Header(default=None, alias="X-Webhook-Signature"),
):
    provider = get_payment_provider()
    payload_bytes = await request.body()
    sig = signature or sandbox_sig

    if not sig or not provider.verify_webhook_signature(payload_bytes, sig):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        import json
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    event_type = payload.get("event", "payment.captured")
    correlation_id = getattr(request.state, "correlation_id", None)
    result = provider.process_webhook_event(db, event_type, payload, correlation_id)
    return result


# ---------------------------------------------------------------------------
# Administrative & Governance Routes (Role-Guarded)
# ---------------------------------------------------------------------------

@admin_router.get("/system-stats", response_model=AdminSystemStatsResponse)
def get_admin_system_stats(
    context: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Administrative platform oversight: aggregated stats, environment, and security posture.
    Strictly role-guarded to users with role='admin'.
    """
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_txs = db.scalar(select(func.count(Transaction.id))) or 0
    total_vol = db.scalar(select(func.sum(Transaction.amount_paise))) or 0
    now = utc_now()
    active_sessions = db.scalar(
        select(func.count(ServerSession.id)).where(
            ServerSession.is_revoked.is_(False),
            ServerSession.expires_at > now,
        )
    ) or 0
    settings = get_settings()

    return AdminSystemStatsResponse(
        total_users=total_users,
        total_transactions=total_txs,
        total_volume_paise=int(total_vol),
        active_sessions=active_sessions,
        environment=settings.environment,
        debug_mode=settings.debug,
        payment_provider=settings.payment_provider,
        database_engine=db.get_bind().dialect.name,
    )


@admin_router.get("/audit-logs", response_model=list[AdminAuditEventResponse])
def get_admin_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None, max_length=40),
    outcome: str | None = Query(default=None, max_length=16),
    context: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Administrative audit log query: view security events across users and IP buckets.
    Strictly role-guarded to users with role='admin'.
    """
    query = select(AuditEvent)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    if outcome:
        query = query.where(AuditEvent.outcome == outcome)
    query = query.order_by(AuditEvent.occurred_at.desc()).offset(offset).limit(limit)
    return db.scalars(query).all()


@admin_router.get("/users", response_model=list[AdminUserListItem])
def get_admin_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Administrative user management: list accounts and verification status.
    Strictly role-guarded to users with role='admin'.
    """
    return db.scalars(select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)).all()


@admin_router.patch("/users/{user_id}/status", response_model=AdminUserListItem)
def update_admin_user_status(
    user_id: str,
    body: AdminUserStatusUpdate,
    request: Request,
    context: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Administrative account governance: activate or suspend user accounts.
    When suspended, all active sessions for that user are immediately revoked.
    Strictly role-guarded to users with role='admin'.
    """
    if user_id == context.user.id:
        raise HTTPException(status_code=400, detail="Cannot alter administrative status of own account.")

    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    target_user.status = body.status
    if body.status == "disabled":
        sessions = db.scalars(
            select(ServerSession).where(
                ServerSession.user_id == user_id,
                ServerSession.is_revoked.is_(False),
            )
        ).all()
        now = utc_now()
        for s in sessions:
            s.is_revoked = True
            s.revoked_at = now

    add_audit(db, "admin_user_status_change", "success", context.user.id, getattr(request.state, "correlation_id", None))
    db.commit()
    db.refresh(target_user)
    return target_user


router.include_router(admin_router)

