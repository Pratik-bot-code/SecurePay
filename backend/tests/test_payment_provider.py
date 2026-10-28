import json
import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.models import DemoAccount, LedgerEntry, PaymentOrder, Transaction, User
from app.services.payment_provider import SandboxPaymentProvider, get_payment_provider


def create_user(client: TestClient, handle: str) -> tuple[dict, str]:
    res = client.post(
        "/api/auth/register",
        json={
            "display_name": f"User {handle}",
            "demo_handle": handle,
            "password": "Correct-Horse-Battery-99!",
        },
    )
    assert res.status_code == 201, res.text
    login = client.post(
        "/api/auth/login",
        json={"demo_handle": handle, "password": "Correct-Horse-Battery-99!"},
    )
    assert login.status_code == 200, login.text
    return res.json()["user"], login.json()["csrf_token"]


@pytest.fixture(autouse=True)
def relaxed_test_rate_limits(monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_register_per_minute", 200)
    monkeypatch.setattr(get_settings(), "rate_limit_login_per_minute", 200)


def test_payment_order_creation_and_idempotency():
    with TestClient(app) as client:
        user, csrf = create_user(client, f"payuser.{secrets.token_hex(4)}")
        idem_key = f"idem-{secrets.token_hex(6)}"

        # 1. Create payment order for ₹500 (50,000 paise)
        order_res = client.post(
            "/api/payments/orders",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": idem_key},
            json={
                "amount_paise": 50000,
                "order_type": "payment",
                "notes": "Testing sandbox order",
            },
        )
        assert order_res.status_code == 201, order_res.text
        data = order_res.json()
        assert data["amount_paise"] == 50000
        assert data["currency"] == "INR"
        assert data["status"] == "created"
        assert "upi://pay?" in data["upi_payment_url"]
        assert "500.00" in data["upi_payment_url"]
        order_ref = data["order_reference"]

        # 2. Re-submit with same idempotency key -> returns existing order
        re_res = client.post(
            "/api/payments/orders",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": idem_key},
            json={
                "amount_paise": 50000,
                "order_type": "payment",
            },
        )
        assert re_res.status_code == 201
        assert re_res.json()["order_reference"] == order_ref

        # 3. Read order by reference
        get_res = client.get(f"/api/payments/orders/{order_ref}")
        assert get_res.status_code == 200
        assert get_res.json()["order_reference"] == order_ref


def test_server_side_payment_signature_verification_and_atomic_settlement():
    with TestClient(app) as client:
        user, csrf = create_user(client, f"settle.{secrets.token_hex(4)}")

        # Dashboard initially has 0 balance
        dash_initial = client.get("/api/dashboard").json()
        assert dash_initial["account"]["balance_paise"] == 0

        # Create order for ₹1,250 (125,000 paise)
        order_res = client.post(
            "/api/payments/orders",
            headers={"X-CSRF-Token": csrf},
            json={"amount_paise": 125000, "order_type": "payment"},
        )
        order_data = order_res.json()
        order_ref = order_data["order_reference"]
        payment_id = f"pay_{order_ref}"

        # 1. Attempt verification with forged signature -> Rejected 400
        fake_verify = client.post(
            "/api/payments/verify",
            headers={"X-CSRF-Token": csrf},
            json={
                "order_reference": order_ref,
                "payment_id": payment_id,
                "signature": "forged_invalid_signature_hex_12345",
            },
        )
        assert fake_verify.status_code == 400
        assert "Verification failed" in fake_verify.json()["detail"]

        # 2. Verify with valid cryptographic signature
        valid_sig = order_data["sandbox_signature"]
        verify_res = client.post(
            "/api/payments/verify",
            headers={"X-CSRF-Token": csrf},
            json={
                "order_reference": order_ref,
                "payment_id": payment_id,
                "signature": valid_sig,
            },
        )
        assert verify_res.status_code == 200, verify_res.text
        assert verify_res.json()["status"] == "paid"

        # 3. Verify user's DemoAccount balance is atomically credited
        dash_after = client.get("/api/dashboard").json()
        assert dash_after["account"]["balance_paise"] == 125000
        assert dash_after["total_received_paise"] == 125000
        assert dash_after["transaction_count"] == 1
        assert len(dash_after["recent_transactions"]) == 1
        assert dash_after["recent_transactions"][0]["amount_paise"] == 125000

        # 4. Verify immutable LedgerEntry was persisted in DB
        with SessionLocal() as db:
            user_acc = db.scalar(select(DemoAccount).where(DemoAccount.user_id == user["id"]))
            assert user_acc.balance_paise == 125000

            ledger = db.scalar(select(LedgerEntry).where(LedgerEntry.account_id == user_acc.id))
            assert ledger is not None
            assert ledger.amount_paise == 125000
            assert ledger.entry_type == "credit"


def test_payment_webhook_signature_verification_and_replay_defense():
    with TestClient(app) as client:
        user, csrf = create_user(client, f"webhook.{secrets.token_hex(4)}")

        # Create order
        order_res = client.post(
            "/api/payments/orders",
            headers={"X-CSRF-Token": csrf},
            json={"amount_paise": 75000, "order_type": "payment"},
        )
        order_data = order_res.json()
        order_id = order_data["order_id"]

        webhook_body = json.dumps({
            "event": "payment.captured",
            "order_id": order_id,
            "payment_id": f"pay_{order_data['order_reference']}",
        }).encode("utf-8")

        # 1. Webhook without signature -> Rejected 400
        bad_webhook = client.post("/api/payments/webhook", content=webhook_body)
        assert bad_webhook.status_code == 400

        # 2. Webhook with valid signature
        provider = SandboxPaymentProvider()
        import hmac, hashlib
        settings = get_settings()
        secret = (settings.razorpay_webhook_secret or settings.session_secret).encode("utf-8")
        valid_webhook_sig = hmac.new(secret, webhook_body, hashlib.sha256).hexdigest()

        ok_webhook = client.post(
            "/api/payments/webhook",
            content=webhook_body,
            headers={"X-Webhook-Signature": valid_webhook_sig, "Content-Type": "application/json"},
        )
        assert ok_webhook.status_code == 200
        assert ok_webhook.json()["status"] == "processed"

        # 3. Replay webhook -> Returns duplicate status without double-crediting
        replay_webhook = client.post(
            "/api/payments/webhook",
            content=webhook_body,
            headers={"X-Webhook-Signature": valid_webhook_sig, "Content-Type": "application/json"},
        )
        assert replay_webhook.status_code == 200
        assert replay_webhook.json()["status"] == "duplicate"


def test_user_cannot_access_other_users_payment_orders():
    with TestClient(app) as client_a:
        user_a, csrf_a = create_user(client_a, f"ordera.{secrets.token_hex(4)}")

        with TestClient(app) as client_b:
            user_b, csrf_b = create_user(client_b, f"orderb.{secrets.token_hex(4)}")

            # User A creates order
            order_res = client_a.post(
                "/api/payments/orders",
                headers={"X-CSRF-Token": csrf_a},
                json={"amount_paise": 10000, "order_type": "payment"},
            )
            order_ref = order_res.json()["order_reference"]

            # User B attempts to read User A's order -> 404 Not Found
            b_read = client_b.get(f"/api/payments/orders/{order_ref}")
            assert b_read.status_code == 404
