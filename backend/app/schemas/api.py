from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_handle(value: str) -> str:
    return value.strip().lower()


class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    demo_handle: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=12, max_length=128)

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("demo_handle")
    @classmethod
    def normalize_demo_handle(cls, value: str) -> str:
        return normalize_handle(value)


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
    def trim_display_name(cls, value: str) -> str:
        return value.strip()

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
