from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DemoAccount, Notification, Transaction, User
from app.schemas.api import NotificationResponse, TransactionResponse, UserResponse


def user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def transaction_response(db: Session, transaction: Transaction, viewer: User) -> TransactionResponse:
    recipient = db.scalar(
        select(DemoAccount).where(DemoAccount.id == transaction.recipient_account_id)
    )
    recipient_user = db.get(User, recipient.user_id) if recipient and recipient.user_id else None
    sender = db.get(DemoAccount, transaction.sender_account_id) if transaction.sender_account_id else None
    sender_user = db.get(User, sender.user_id) if sender and sender.user_id else None
    viewer_is_sender = bool(sender_user and sender_user.id == viewer.id)
    counterparty = (recipient_user if viewer_is_sender else sender_user) or None
    if transaction.transaction_type == "demo_grant":
        display_name = transaction.counterparty_label or "SecurePay demo fund"
        handle = transaction.counterparty_handle or "demo-fund"
        initials = "SD"
        color = "yellow"
        signed = transaction.amount_paise
        method = "SecurePay simulated receive"
    elif counterparty is None:
        display_name = "SecurePay demo fund"
        handle = "demo-fund"
        initials = "SD"
        color = "yellow"
        signed = transaction.amount_paise
        method = "SecurePay simulated demo credit"
    else:
        display_name = counterparty.display_name
        handle = counterparty.demo_handle
        initials = "".join(part[0] for part in display_name.split()[:2]).upper()
        colors = ("lavender", "peach", "mint", "blue")
        color = colors[sum(handle.encode("utf-8")) % len(colors)]
        signed = -transaction.amount_paise if viewer_is_sender else transaction.amount_paise
        method = "SecurePay simulated transfer"
    return TransactionResponse(
        id=transaction.id,
        reference=transaction.reference,
        transaction_type=transaction.transaction_type,
        amount_paise=transaction.amount_paise,
        signed_amount_paise=signed,
        name=display_name,
        handle=handle,
        initials=initials,
        color=color,
        category=transaction.category,
        note=transaction.note if viewer_is_sender else None,
        status="Completed",
        method=method,
        created_at=transaction.created_at,
    )


def notification_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        title=notification.title,
        body=notification.body,
        icon=notification.icon,
        created_at=notification.created_at,
        unread=notification.read_at is None,
    )
