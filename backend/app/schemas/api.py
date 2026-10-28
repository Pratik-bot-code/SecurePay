from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


TAG_RE = re.compile(r"<[^>]+?>")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def sanitize_text(value: str) -> str:
    """
    Sanitize text input to prevent XSS, HTML injection, and control-character attacks.
    """
    if not value:
        return ""
    # Strip HTML tags
    cleaned = TAG_RE.sub("", value)
    # Strip dangerous control characters
    cleaned = CONTROL_CHARS_RE.sub("", cleaned)
    return cleaned.strip()


def normalize_handle(value: str) -> str:
    return value.strip().lower()


COMMON_WEAK_PASSWORDS = {
    "password1234",
    "password12345",
    "123456789012",
    "qwerty123456",
    "administrator",
    "admin1234567",
    "admin12345678",
    "securepay1234",
    "changeme1234",
    "welcome12345",
}


def validate_password_strength(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long.")
    if len(password) > 128:
        raise ValueError("Password cannot exceed 128 characters.")
    if len(set(password)) < 4:
        raise ValueError("Password is too simple. Use a wider variety of characters.")
    if password.lower() in COMMON_WEAK_PASSWORDS:
        raise ValueError("Password is too common. Please choose a stronger, unique passphrase.")
    if password.isdigit():
        raise ValueError("Password cannot consist solely of digits.")
    if password.isalpha() and (password.islower() or password.isupper()):
        raise ValueError("Password must contain a mix of uppercase, lowercase, numbers, or special symbols.")
    return password


class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    demo_handle: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=12, max_length=128)

    @field_validator("display_name")
    @classmethod
    def sanitize_display_name(cls, value: str) -> str:
        cleaned = sanitize_text(value)
        if not cleaned:
            raise ValueError("Display name cannot be empty or solely HTML tags.")
        return cleaned

    @field_validator("demo_handle")
    @classmethod
    def normalize_demo_handle(cls, value: str) -> str:
        return normalize_handle(value)

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    demo_handle: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("demo_handle")
    @classmethod
    def normalize_demo_handle(cls, value: str) -> str:
        return normalize_handle(value)


class ProfileUpdateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    demo_handle: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9._-]+$")

    @field_validator("display_name")
    @classmethod
    def sanitize_display_name(cls, value: str) -> str:
        cleaned = sanitize_text(value)
        if not cleaned:
            raise ValueError("Display name cannot be empty or solely HTML tags.")
        return cleaned

    @field_validator("demo_handle")
    @classmethod
    def normalize_demo_handle(cls, value: str) -> str:
        return normalize_handle(value)


class PreferencesUpdateRequest(BaseModel):
    biometric_preference: bool
    security_alerts: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_new_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class NotificationReadRequest(BaseModel):
    read: bool


class UserResponse(BaseModel):
    id: str
    display_name: str
    demo_handle: str
    role: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AccountResponse(BaseModel):
    balance_paise: int
    currency: str = "INR"


class SessionResponse(BaseModel):
    id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool
    label: str


class TransactionResponse(BaseModel):
    id: str | None = None
    reference: str
    transaction_type: Literal["transfer", "demo_grant"]
    amount_paise: int
    signed_amount_paise: int
    name: str
    handle: str
    initials: str
    color: str
    category: str
    note: str | None
    status: str
    method: str
    created_at: datetime


class TransactionSummary(BaseModel):
    total_credits_paise: int = 0
    total_debits_paise: int = 0
    pending_count: int = 0
    successful_count: int = 0
    failed_count: int = 0


class PaginatedTransactionsResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: TransactionSummary


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    icon: str
    created_at: datetime
    unread: bool


class DashboardResponse(BaseModel):
    user: UserResponse
    account: AccountResponse
    monthly_spend_paise: int
    total_received_paise: int
    total_sent_paise: int
    transaction_count: int
    recent_transactions: list[TransactionResponse]
    notifications_unread: int


class LinkedBankAccountCreate(BaseModel):
    bank_name: str = Field(min_length=2, max_length=100)
    account_holder_name: str = Field(min_length=2, max_length=100)
    account_number: str = Field(min_length=9, max_length=18, pattern=r"^[0-9]+$")
    ifsc_code: str = Field(min_length=11, max_length=11, pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")
    account_type: Literal["savings", "current"] = "savings"

    @field_validator("bank_name", "account_holder_name")
    @classmethod
    def sanitize_bank_fields(cls, value: str) -> str:
        cleaned = sanitize_text(value)
        if not cleaned:
            raise ValueError("Field cannot be empty or solely HTML tags.")
        return cleaned

    @field_validator("ifsc_code")
    @classmethod
    def uppercase_ifsc(cls, value: str) -> str:
        return value.strip().upper()


class LinkedBankAccountResponse(BaseModel):
    id: str
    bank_name: str
    account_holder_name: str
    masked_account_number: str
    ifsc_code: str
    account_type: str
    is_primary: bool
    verification_status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BankDirectoryEntry(BaseModel):
    code: str
    name: str
    short_name: str
    category: str
    ifsc_prefix: str
    popular: bool
    active: bool
    supported_for_linking: bool
    linking_method: str
    supported_features: list[str]
    tagline: str


class RecipientValidateRequest(BaseModel):
    identifier: str = Field(min_length=2, max_length=100)
    identifier_type: Literal["upi_id", "mobile", "handle"] = "upi_id"

    @field_validator("identifier")
    @classmethod
    def sanitize_identifier(cls, value: str) -> str:
        return sanitize_text(value)


class RecipientValidateResponse(BaseModel):
    valid: bool
    identifier_type: str
    normalized_identifier: str
    display_name: str | None = None
    verified: bool = False
    verification_source: str = "sandbox"
    message: str = ""


class MerchantRegisterRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=60, default="General Merchant")

    @field_validator("business_name", "category")
    @classmethod
    def sanitize_merchant_fields(cls, value: str) -> str:
        cleaned = sanitize_text(value)
        if not cleaned:
            raise ValueError("Field cannot be empty or solely HTML tags.")
        return cleaned


class MerchantResponse(BaseModel):
    id: str
    business_name: str
    merchant_code: str
    category: str
    upi_handle: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentStatusHistoryResponse(BaseModel):
    id: str
    payment_order_id: str
    old_status: str
    new_status: str
    reason: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentOrderResponse(BaseModel):
    id: str
    order_reference: str
    provider_name: str
    provider_order_id: str | None
    amount_paise: int
    currency: str
    status: str
    order_type: str
    recipient_identifier: str | None = None
    recipient_type: str | None = None
    recipient_display_name: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentOrderCreateRequest(BaseModel):
    amount_paise: int = Field(gt=0, le=10_000_000)  # Up to ₹100,000 per order
    order_type: Literal["payment", "transfer", "merchant_checkout"] = "payment"
    notes: str | None = Field(default=None, max_length=200)
    recipient_identifier: str | None = Field(default=None, max_length=100)
    recipient_type: Literal["upi_id", "mobile", "handle"] | None = None

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_text(value)


class PaymentOrderCreateResponse(BaseModel):
    order_id: str
    order_reference: str
    amount_paise: int
    currency: str
    provider_name: str
    provider_order_id: str | None
    upi_payment_url: str
    status: str
    sandbox_mode: bool = True
    sandbox_signature: str | None = None  # Helper for sandbox UI verification


class PaymentVerifyRequest(BaseModel):
    order_reference: str = Field(min_length=5, max_length=50)
    payment_id: str = Field(min_length=5, max_length=100)
    signature: str = Field(min_length=10, max_length=128)


# ---------------------------------------------------------------------------
# Admin Schemas
# ---------------------------------------------------------------------------

class AdminSystemStatsResponse(BaseModel):
    total_users: int
    total_transactions: int
    total_volume_paise: int
    active_sessions: int
    environment: str
    debug_mode: bool
    payment_provider: str
    database_engine: str


class AdminAuditEventResponse(BaseModel):
    id: str
    user_id: str | None
    event_type: str
    outcome: str
    correlation_id: str | None
    occurred_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminUserListItem(BaseModel):
    id: str
    display_name: str
    demo_handle: str
    role: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminUserStatusUpdate(BaseModel):
    status: Literal["active", "disabled"]
