import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.config import Settings, get_settings
from app.main import app
from app.models import AuditEvent


def register(client: TestClient, handle: str) -> tuple[dict, str]:
    response = client.post(
        "/api/auth/register",
        json={
            "display_name": f"Demo {handle}",
            "demo_handle": handle,
            "password": "test-only-password-123!",
        },
    )
    assert response.status_code == 201, response.text
    login = client.post(
        "/api/auth/login",
        json={"demo_handle": handle, "password": "test-only-password-123!"},
    )
    assert login.status_code == 200, login.text
    return response.json()["user"], login.json()["csrf_token"]


def test_registration_requires_a_separate_login():
    with TestClient(app) as client:
        handle = f"register.{secrets.token_hex(4)}"
        response = client.post(
            "/api/auth/register",
            json={
                "display_name": "New account",
                "demo_handle": handle,
                "password": "test-only-password-123!",
            },
        )

        assert response.status_code == 201, response.text
        assert "csrf_token" not in response.json()
        assert client.get("/api/auth/session").status_code == 401

        login = client.post(
            "/api/auth/login",
            json={"demo_handle": handle, "password": "test-only-password-123!"},
        )
        assert login.status_code == 200
        assert client.get("/api/auth/session").status_code == 200


@pytest.fixture(autouse=True)
def relaxed_test_rate_limits(monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_register_per_minute", 100)


def test_users_cannot_read_or_change_each_others_data():
    suffix = secrets.token_hex(4)
    with TestClient(app) as alice_client, TestClient(app) as bob_client:
        alice, alice_csrf = register(alice_client, f"alice.{suffix}")
        bob, bob_csrf = register(bob_client, f"bob.{suffix}")
        alice_headers = {"X-CSRF-Token": alice_csrf}
        assert bob_csrf

        alice_profile = alice_client.get("/api/profile").json()
        bob_profile = bob_client.get("/api/profile").json()
        bob_session = bob_client.get("/api/auth/sessions").json()[0]
        bob_notification = bob_client.get("/api/notifications").json()[0]
        bob_reference = "not-a-provider-reference"
        alice_balance = alice_client.get("/api/dashboard").json()["account"]["balance_paise"]

        assert alice_client.get(f"/api/transactions/{bob_reference}").status_code == 404
        assert alice_client.patch(
            f"/api/notifications/{bob_notification['id']}",
            headers=alice_headers,
            json={"read": True},
        ).status_code == 404
        assert alice_client.delete(
            f"/api/auth/sessions/{bob_session['id']}",
            headers=alice_headers,
        ).status_code == 404
        assert alice_client.post(
            "/api/transfers",
            headers={**alice_headers, "Idempotency-Key": f"cross-user-{suffix}"},
            json={
                "recipient_handle": bob["demo_handle"],
                "amount_paise": 100,
                "approval_password": "test-only-password-123!",
            },
        ).status_code == 503

        updated = alice_client.patch(
            "/api/profile",
            headers=alice_headers,
            json={"display_name": "Updated Alice", "demo_handle": alice["demo_handle"]},
        )
        assert updated.status_code == 200
        assert alice_client.get("/api/profile").json()["display_name"] == "Updated Alice"
        assert bob_client.get("/api/profile").json() == bob_profile
        assert bob_client.get("/api/notifications").json()[0]["unread"] == bob_notification["unread"]
        assert bob_client.get("/api/auth/sessions").json()[0]["id"] == bob_session["id"]
        assert alice_client.get("/api/dashboard").json()["account"]["balance_paise"] == alice_balance
        assert alice_profile["id"] != bob_profile["id"]


def test_payment_routes_stay_unavailable_without_provider():
    suffix = secrets.token_hex(4)
    with TestClient(app) as client:
        _, csrf = register(client, f"account.{suffix}")
        dashboard = client.get("/api/dashboard").json()
        assert dashboard["account"]["balance_paise"] == 0
        assert dashboard["transaction_count"] == 0
        assert dashboard["recent_transactions"] == []
        assert client.get("/api/transactions").json() == []
        assert client.get("/api/directory").json() == []

        response = client.post(
            "/api/transfers",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": f"disabled-{suffix}"},
            json={
                "recipient_handle": "maya.patel",
                "amount_paise": 1_000,
                "approval_password": "test-only-password-123!",
            },
        )
        assert response.status_code == 503
        assert "approved payment provider" in response.json()["detail"]
        assert client.get("/api/dashboard").json()["account"]["balance_paise"] == 0
        assert not any("receipt" in path for path in app.openapi()["paths"])


def test_unsafe_requests_require_session_bound_csrf_token():
    with TestClient(app) as client:
        handle = f"csrf.{secrets.token_hex(4)}"
        _, csrf = register(client, handle)
        response = client.patch(
            "/api/profile",
            json={"display_name": "No CSRF", "demo_handle": f"csrf.{secrets.token_hex(4)}"},
        )
        assert response.status_code == 403

        logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
        assert logout.status_code == 204
        assert client.get("/api/dashboard").status_code == 401


def test_password_change_rotates_session_and_revokes_other_sessions():
    suffix = secrets.token_hex(4)
    handle = f"password.{suffix}"
    with TestClient(app) as primary, TestClient(app) as secondary:
        register(primary, handle)
        login = secondary.post(
            "/api/auth/login",
            json={"demo_handle": handle, "password": "test-only-password-123!"},
        )
        assert login.status_code == 200
        second_csrf = login.json()["csrf_token"]

        changed = primary.put(
            "/api/auth/password",
            headers={"X-CSRF-Token": primary.get("/api/auth/session").json()["csrf_token"]},
            json={
                "current_password": "test-only-password-123!",
                "new_password": "test-only-new-password-456!",
            },
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["revoked_other_sessions"] == 1
        assert primary.get("/api/dashboard").status_code == 200
        assert secondary.get("/api/dashboard").status_code == 401
        assert primary.patch(
            "/api/profile",
            headers={"X-CSRF-Token": changed.json()["csrf_token"]},
            json={"display_name": "Updated password user", "demo_handle": handle},
        ).status_code == 200
        assert second_csrf != changed.json()["csrf_token"]


def test_failed_signin_creates_security_alert_and_correlated_audit():
    with TestClient(app) as client:
        handle = f"failed.login.{secrets.token_hex(4)}"
        user, _ = register(client, handle)
        response = client.post(
            "/api/auth/login",
            json={"demo_handle": handle, "password": "incorrect-invalid-password"},
        )
        assert response.status_code == 401
        request_id = response.headers["X-Request-ID"]
        alerts = client.get("/api/notifications").json()
        assert any(item["title"] == "Unsuccessful sign-in attempt" for item in alerts)

        with SessionLocal() as db:
            event = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.user_id == user["id"],
                    AuditEvent.event_type == "login",
                    AuditEvent.outcome == "denied",
                    AuditEvent.correlation_id == request_id,
                )
            )
            assert event is not None


def test_recovery_is_explicitly_unavailable_without_verified_contact():
    with TestClient(app) as client:
        response = client.post("/api/auth/recovery", json={})
        assert response.status_code == 503
        assert "verified contact method" in response.json()["detail"]


def test_production_requires_postgres_tls_and_secure_cookie():
    settings = Settings(
        environment="production",
        session_secret="p" * 48,
        session_cookie_secure=True,
        cors_origins=["https://securepay.example"],
        database_url="postgresql+psycopg://user:password@db.example/securepay?sslmode=verify-full",
    )
    settings.validate_production()

    settings.database_url = "postgresql+psycopg://user:password@db.example/securepay"
    with pytest.raises(RuntimeError, match="sslmode=verify-full"):
        settings.validate_production()
