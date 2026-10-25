from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(demo_handle) BETWEEN 3 AND 30", name="ck_users_handle_length"),
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    demo_handle: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(12), nullable=False, default="user")
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="active")
    is_directory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    biometric_preference: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    security_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class DemoAccount(Base):
    __tablename__ = "demo_accounts"
    __table_args__ = (
        CheckConstraint(
            "(account_type = 'system_offset' AND balance_paise <= 0) OR (account_type <> 'system_offset' AND balance_paise >= 0)",
            name="ck_demo_accounts_balance_nonnegative",
        ),
        CheckConstraint("currency = 'INR'", name="ck_demo_accounts_currency"),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_demo_accounts_status"),
        CheckConstraint("account_type IN ('user', 'system', 'system_offset')", name="ck_demo_accounts_type"),
        CheckConstraint(
            "(account_type = 'user' AND user_id IS NOT NULL) OR (account_type <> 'user' AND user_id IS NULL)",
            name="ck_demo_accounts_owner_type",
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id", ondelete="RESTRICT"), unique=True)
    label: Mapped[str] = mapped_column(String(60), nullable=False, default="SecurePay account")
    account_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    balance_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_transactions_amount_positive"),
        CheckConstraint("status IN ('posted')", name="ck_transactions_status"),
        CheckConstraint("transaction_type IN ('transfer', 'demo_grant')", name="ck_transactions_type"),
        CheckConstraint("currency = 'INR'", name="ck_transactions_currency"),
        CheckConstraint("sender_account_id IS NULL OR sender_account_id <> recipient_account_id", name="ck_transactions_distinct_accounts"),
        CheckConstraint(
            "(transaction_type = 'transfer' AND sender_account_id IS NOT NULL) OR transaction_type = 'demo_grant'",
            name="ck_transactions_sender_type",
        ),
        Index("ix_transactions_sender_created", "sender_account_id", "created_at"),
        Index("ix_transactions_recipient_created", "recipient_account_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    reference: Mapped[str] = mapped_column(String(24), nullable=False, unique=True, index=True)
    transaction_type: Mapped[str] = mapped_column(String(16), nullable=False, default="transfer")
    sender_account_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("demo_accounts.id", ondelete="RESTRICT"))
    recipient_account_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("demo_accounts.id", ondelete="RESTRICT"), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    category: Mapped[str] = mapped_column(String(48), nullable=False, default="Demo transfer")
    note: Mapped[str | None] = mapped_column(String(80))
    counterparty_label: Mapped[str | None] = mapped_column(String(60))
    counterparty_handle: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="posted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_paise <> 0", name="ck_ledger_entries_nonzero"),
        CheckConstraint(
            "(entry_type = 'debit' AND amount_paise < 0) OR (entry_type = 'credit' AND amount_paise > 0)",
            name="ck_ledger_entries_type_amount",
        ),
        UniqueConstraint("transaction_id", "entry_type", name="uq_ledger_transaction_entry_type"),
        Index("ix_ledger_account_created", "account_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    transaction_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False)
    account_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("demo_accounts.id", ondelete="RESTRICT"), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class ServerSession(Base):
    __tablename__ = "server_sessions"
    __table_args__ = (
        Index("ix_sessions_user_expiry", "user_id", "expires_at"),
        CheckConstraint("revoked_at IS NULL OR revoked_at >= created_at", name="ck_sessions_revoked_after_created"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("user_id", "operation", "key", name="uq_idempotency_user_operation_key"),
        UniqueConstraint("transaction_id", name="uq_idempotency_transaction"),
        Index("ix_idempotency_expiry", "expires_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    operation: Mapped[str] = mapped_column(String(24), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("transactions.id", ondelete="RESTRICT"))
    result_status: Mapped[str] = mapped_column(String(16), nullable=False, default="complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("transactions.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(String(240), nullable=False)
    icon: Mapped[str] = mapped_column(String(16), nullable=False, default="sparkles")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "security_audit_events"
    __table_args__ = (Index("ix_audit_user_time", "user_id", "occurred_at"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    correlation_id: Mapped[str | None] = mapped_column(String(64))


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    __table_args__ = (UniqueConstraint("key_hash", "window_start", name="uq_rate_bucket_key_window"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    window_start: Mapped[int] = mapped_column(BigInteger, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"))
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
