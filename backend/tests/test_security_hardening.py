import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import utc_now
from app.main import app
from app.models import AuditEvent, ServerSession, User


def create_user(client: TestClient, handle: str, password: str = "StrongPassphrase2026!") -> tuple[dict, str]:
    res = client.post(
        "/api/auth/register",
        json={
            "display_name": f"User {handle}",
            "demo_handle": handle,
            "password": password,
        },
    )
    assert res.status_code == 201, res.text
    login = client.post(
        "/api/auth/login",
        json={"demo_handle": handle, "password": password},
    )
    assert login.status_code == 200, login.text
    return res.json()["user"], login.json()["csrf_token"]


@pytest.fixture(autouse=True)
def relaxed_test_rate_limits(monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_register_per_minute", 200)
    monkeypatch.setattr(get_settings(), "rate_limit_login_per_minute", 200)


def test_password_strength_enforcement():
    with TestClient(app) as client:
        # 1. Purely numeric
        res1 = client.post(
            "/api/auth/register",
            json={
                "display_name": "Numeric User",
                "demo_handle": f"user.{secrets.token_hex(4)}",
                "password": "12345678901234",
            },
        )
        assert res1.status_code == 422
        assert "cannot consist solely of digits" in res1.text

        # 2. Repeated characters
        res2 = client.post(
            "/api/auth/register",
            json={
                "display_name": "Repeat User",
                "demo_handle": f"user.{secrets.token_hex(4)}",
                "password": "aaaaaaaaaaaaaaaa",
            },
        )
        assert res2.status_code == 422
        assert "too simple" in res2.text

        # 3. Known common password
        res3 = client.post(
            "/api/auth/register",
            json={
                "display_name": "Common User",
                "demo_handle": f"user.{secrets.token_hex(4)}",
                "password": "password12345",
            },
        )
        assert res3.status_code == 422
        assert "too common" in res3.text

        # 4. Purely lowercase alphabetic without variation
        res4 = client.post(
            "/api/auth/register",
            json={
                "display_name": "Alpha User",
                "demo_handle": f"user.{secrets.token_hex(4)}",
                "password": "alllowercaseletters",
            },
        )
        assert res4.status_code == 422
        assert "mix of uppercase, lowercase, numbers, or special symbols" in res4.text

        # 5. Strong passphrase succeeds
        handle = f"strong.{secrets.token_hex(4)}"
        res5 = client.post(
            "/api/auth/register",
            json={
                "display_name": "Strong User",
                "demo_handle": handle,
                "password": "Correct-Horse-Battery-99!",
            },
        )
        assert res5.status_code == 201


def test_session_last_seen_at_updates():
    with TestClient(app) as client:
        handle = f"session.{secrets.token_hex(4)}"
        user, _ = create_user(client, handle)

        with SessionLocal() as db:
            session_before = db.scalar(
                select(ServerSession).where(
                    ServerSession.user_id == user["id"],
                    ServerSession.is_revoked.is_(False),
                )
            )
            assert session_before is not None
            initial_last_seen = session_before.last_seen_at

        # Make an authenticated request
        res = client.get("/api/auth/session")
        assert res.status_code == 200

        with SessionLocal() as db:
            session_after = db.scalar(
                select(ServerSession).where(
                    ServerSession.user_id == user["id"],
                    ServerSession.is_revoked.is_(False),
                )
            )
            assert session_after is not None
            assert session_after.last_seen_at >= initial_last_seen


def test_csrf_protection_and_origin_verification():
    with TestClient(app) as client:
        handle = f"csrf.{secrets.token_hex(4)}"
        create_user(client, handle)

        # 1. Missing CSRF header on unsafe request (POST /api/auth/logout)
        res_missing = client.post("/api/auth/logout")
        assert res_missing.status_code == 403
        assert "CSRF" in res_missing.json()["detail"]

        # 2. Tampered CSRF header
        res_tampered = client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": "tampered_invalid_csrf_token_value"},
        )
        assert res_tampered.status_code == 403
        assert "CSRF" in res_tampered.json()["detail"]

        # 3. Disallowed origin header
        res_origin = client.post(
            "/api/auth/logout",
            headers={
                "X-CSRF-Token": "any",
                "Origin": "https://malicious-attacker-site.com",
            },
        )
        assert res_origin.status_code == 403
        assert "origin" in res_origin.json()["detail"].lower()


def test_request_body_size_limit_64kb():
    with TestClient(app) as client:
        # Send a request with body > 64KB
        large_body = "x" * (65 * 1024)
        response = client.post(
            "/api/auth/register",
            content=large_body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(large_body))},
        )
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()
        assert "X-Request-ID" in response.headers


def test_security_headers_present():
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        headers = res.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Referrer-Policy") == "no-referrer"
        assert "camera=()" in headers.get("Permissions-Policy", "")
        assert "default-src 'none'" in headers.get("Content-Security-Policy", "")
        assert "X-Request-ID" in headers

        # Swagger docs route has relaxed CSP for docs rendering
        docs_res = client.get("/api/docs")
        if docs_res.status_code == 200:
            assert "default-src 'self'" in docs_res.headers.get("Content-Security-Policy", "")


def test_rate_limiting_registration_enforced(monkeypatch):
    unique_ip = f"198.51.100.{secrets.randbelow(200) + 10}"
    with TestClient(app, client=(unique_ip, 50000)) as client:
        # Set low rate limit to trigger
        monkeypatch.setattr(get_settings(), "rate_limit_register_per_minute", 2)
        h1 = f"rl1.{secrets.token_hex(4)}"
        h2 = f"rl2.{secrets.token_hex(4)}"
        h3 = f"rl3.{secrets.token_hex(4)}"

        r1 = client.post("/api/auth/register", json={"display_name": "U1", "demo_handle": h1, "password": "StrongPassword2026!"})
        assert r1.status_code == 201

        r2 = client.post("/api/auth/register", json={"display_name": "U2", "demo_handle": h2, "password": "StrongPassword2026!"})
        assert r2.status_code == 201

        # 3rd should be rate limited
        r3 = client.post("/api/auth/register", json={"display_name": "U3", "demo_handle": h3, "password": "StrongPassword2026!"})
        assert r3.status_code == 429
        assert "Too many attempts" in r3.json()["detail"]


def test_cannot_revoke_other_users_sessions():
    with TestClient(app) as client_a:
        handle_a = f"usera.{secrets.token_hex(4)}"
        user_a, csrf_a = create_user(client_a, handle_a)

        with TestClient(app) as client_b:
            handle_b = f"userb.{secrets.token_hex(4)}"
            user_b, csrf_b = create_user(client_b, handle_b)

            # User B gets their session ID
            sessions_b = client_b.get("/api/auth/sessions").json()
            session_b_id = sessions_b[0]["id"]

            # User A attempts to revoke User B's session ID using User A's CSRF
            attack_res = client_a.delete(
                f"/api/auth/sessions/{session_b_id}",
                headers={"X-CSRF-Token": csrf_a},
            )
            assert attack_res.status_code == 404

            # Verify User B's session remains active and unrevoked
            with SessionLocal() as db:
                session_b = db.get(ServerSession, session_b_id)
                assert session_b is not None
                assert session_b.is_revoked is False


def test_admin_routes_protection():
    with TestClient(app) as normal_client:
        handle_user = f"norm.{secrets.token_hex(4)}"
        user_norm, csrf_norm = create_user(normal_client, handle_user)

        # 1. Non-admin user denied access to admin routes
        res_stats_denied = normal_client.get("/api/admin/system-stats", headers={"X-CSRF-Token": csrf_norm})
        assert res_stats_denied.status_code == 403
        assert "Administrative privileges required" in res_stats_denied.json()["detail"]

        res_logs_denied = normal_client.get("/api/admin/audit-logs", headers={"X-CSRF-Token": csrf_norm})
        assert res_logs_denied.status_code == 403

        # 2. Promote an admin user in database
        with TestClient(app) as admin_client:
            handle_admin = f"adm.{secrets.token_hex(4)}"
            user_admin, csrf_admin = create_user(admin_client, handle_admin)
            with SessionLocal() as db:
                adm_entity = db.get(User, user_admin["id"])
                adm_entity.role = "admin"
                db.commit()

            # Admin can access system stats
            res_stats = admin_client.get("/api/admin/system-stats", headers={"X-CSRF-Token": csrf_admin})
            assert res_stats.status_code == 200
            stats_data = res_stats.json()
            assert "total_users" in stats_data
            assert "active_sessions" in stats_data
            assert stats_data["debug_mode"] is False

            # Admin can query audit logs
            res_logs = admin_client.get("/api/admin/audit-logs", headers={"X-CSRF-Token": csrf_admin})
            assert res_logs.status_code == 200
            assert isinstance(res_logs.json(), list)

            # Admin can disable the normal user
            res_suspend = admin_client.patch(
                f"/api/admin/users/{user_norm['id']}/status",
                json={"status": "disabled"},
                headers={"X-CSRF-Token": csrf_admin},
            )
            assert res_suspend.status_code == 200
            assert res_suspend.json()["status"] == "disabled"

            # Disabled user's active session is now invalidated
            res_suspended_access = normal_client.get("/api/profile")
            assert res_suspended_access.status_code == 401

            # Admin cannot disable themselves
            res_self_suspend = admin_client.patch(
                f"/api/admin/users/{user_admin['id']}/status",
                json={"status": "disabled"},
                headers={"X-CSRF-Token": csrf_admin},
            )
            assert res_self_suspend.status_code == 400


def test_xss_form_sanitization():
    with TestClient(app) as client:
        handle = f"xss.{secrets.token_hex(4)}"
        # Input containing script and HTML tags
        malicious_display = "<script>alert('XSS')</script>Trusted FinTech User"
        res = client.post(
            "/api/auth/register",
            json={
                "display_name": malicious_display,
                "demo_handle": handle,
                "password": "StrongPassword2026!",
            },
        )
        assert res.status_code == 201
        stored_user = res.json()["user"]
        # Script tags must be completely stripped
        assert "<script>" not in stored_user["display_name"]
        assert "</script>" not in stored_user["display_name"]
        assert "Trusted FinTech User" in stored_user["display_name"]


def test_security_headers_enhanced():
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("X-XSS-Protection") == "1; mode=block"
        assert res.headers.get("Cross-Origin-Opener-Policy") == "same-origin"
        assert res.headers.get("Cross-Origin-Resource-Policy") == "same-origin"
        assert res.headers.get("Referrer-Policy") == "no-referrer"

