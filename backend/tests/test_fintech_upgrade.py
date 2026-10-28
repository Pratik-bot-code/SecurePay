import secrets
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def register_user(client: TestClient, handle: str) -> tuple[dict, str]:
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
def relaxed_rate_limits(monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_register_per_minute", 200)
    monkeypatch.setattr(get_settings(), "rate_limit_login_per_minute", 200)


def test_bank_directory_endpoints():
    with TestClient(app) as client:
        _, csrf = register_user(client, f"bankuser.{secrets.token_hex(4)}")

        # 1. List all banks
        res = client.get("/api/banks/directory")
        assert res.status_code == 200
        banks = res.json()
        assert len(banks) >= 15
        sbi = next((b for b in banks if b["code"] == "SBIN"), None)
        assert sbi is not None
        assert sbi["name"] == "State Bank of India"
        assert sbi["supported_for_linking"] is True

        # 2. Filter by category
        res_cat = client.get("/api/banks/directory?category=private_sector")
        assert res_cat.status_code == 200
        priv = res_cat.json()
        assert all(b["category"] == "private_sector" for b in priv)
        assert any(b["code"] == "HDFC" for b in priv)

        # 3. Search banks
        res_search = client.get("/api/banks/directory?search=kotak")
        assert res_search.status_code == 200
        assert any("Kotak" in b["name"] for b in res_search.json())

        # 4. Lookup by IFSC
        res_lookup = client.get("/api/banks/lookup/HDFC0001234")
        assert res_lookup.status_code == 200
        assert res_lookup.json()["code"] == "HDFC"


def test_recipient_validation():
    with TestClient(app) as client_alice, TestClient(app) as client_bob:
        user_alice, csrf_alice = register_user(client_alice, f"alice.{secrets.token_hex(4)}")
        user_bob, _ = register_user(client_bob, f"bob.{secrets.token_hex(4)}")

        headers = {"X-CSRF-Token": csrf_alice}

        # 1. Valid platform handle
        v_handle = client_alice.post(
            "/api/payments/validate-recipient",
            headers=headers,
            json={"identifier": user_bob["demo_handle"], "identifier_type": "handle"},
        )
        assert v_handle.status_code == 200, v_handle.text
        h_data = v_handle.json()
        assert h_data["valid"] is True
        assert h_data["verified"] is True
        assert h_data["display_name"] == user_bob["display_name"]

        # 2. Valid platform UPI ID
        v_upi_plat = client_alice.post(
            "/api/payments/validate-recipient",
            headers=headers,
            json={"identifier": f"{user_bob['demo_handle']}@securepay", "identifier_type": "upi_id"},
        )
        assert v_upi_plat.status_code == 200
        assert v_upi_plat.json()["verified"] is True

        # 3. Valid external UPI format (sandbox indicator)
        v_upi_ext = client_alice.post(
            "/api/payments/validate-recipient",
            headers=headers,
            json={"identifier": "vendor@okaxis", "identifier_type": "upi_id"},
        )
        assert v_upi_ext.status_code == 200
        assert v_upi_ext.json()["valid"] is True
        assert v_upi_ext.json()["verification_source"] == "sandbox"

        # 4. Invalid UPI ID
        v_upi_bad = client_alice.post(
            "/api/payments/validate-recipient",
            headers=headers,
            json={"identifier": "not_an_upi_id", "identifier_type": "upi_id"},
        )
        assert v_upi_bad.status_code == 200
        assert v_upi_bad.json()["valid"] is False

        # 5. Valid Indian mobile number
        v_mob_ok = client_alice.post(
            "/api/payments/validate-recipient",
            headers=headers,
            json={"identifier": "+91 9876543210", "identifier_type": "mobile"},
        )
        assert v_mob_ok.status_code == 200
        assert v_mob_ok.json()["valid"] is True
        assert v_mob_ok.json()["normalized_identifier"] == "9876543210"

        # 6. Invalid mobile number
        v_mob_bad = client_alice.post(
            "/api/payments/validate-recipient",
            headers=headers,
            json={"identifier": "12345", "identifier_type": "mobile"},
        )
        assert v_mob_bad.status_code == 200
        assert v_mob_bad.json()["valid"] is False


def test_paginated_transactions_and_csv_export():
    with TestClient(app) as client:
        user, csrf = register_user(client, f"ledger.{secrets.token_hex(4)}")
        headers = {"X-CSRF-Token": csrf}

        # Fund account with 2 sandbox payments
        for amt in [20000, 30000]:
            o = client.post(
                "/api/payments/orders",
                headers=headers,
                json={"amount_paise": amt, "order_type": "payment"},
            ).json()
            client.post(
                "/api/payments/verify",
                headers=headers,
                json={
                    "order_reference": o["order_reference"],
                    "payment_id": f"pay_{o['order_reference']}",
                    "signature": o["sandbox_signature"],
                },
            )

        # Query summary
        summary = client.get("/api/transactions/summary").json()
        assert summary["total_credits_paise"] == 50000
        assert summary["successful_count"] == 2

        # Query paginated
        paginated = client.get("/api/transactions?paginated=true&page=1&page_size=10").json()
        assert paginated["total"] == 2
        assert len(paginated["transactions"]) == 2
        assert paginated["summary"]["total_credits_paise"] == 50000

        # Query CSV export
        export = client.get("/api/transactions/export")
        assert export.status_code == 200
        assert "text/csv" in export.headers["content-type"]
        assert "Reference" in export.text
        assert "500.00" in export.text or "300.00" in export.text


def test_payment_status_history_tracking():
    with TestClient(app) as client:
        user, csrf = register_user(client, f"history.{secrets.token_hex(4)}")
        headers = {"X-CSRF-Token": csrf}

        # 1. Create order
        o = client.post(
            "/api/payments/orders",
            headers=headers,
            json={"amount_paise": 500000, "notes": "₹5000 test order"},
        ).json()
        order_ref = o["order_reference"]

        # 2. Check history
        h1 = client.get(f"/api/payments/orders/{order_ref}/history").json()
        assert len(h1) >= 1
        assert h1[0]["new_status"] == "created"

        # 3. Verify payment
        client.post(
            "/api/payments/verify",
            headers=headers,
            json={
                "order_reference": order_ref,
                "payment_id": f"pay_{order_ref}",
                "signature": o["sandbox_signature"],
            },
        )

        # 4. Check history after verification
        h2 = client.get(f"/api/payments/orders/{order_ref}/history").json()
        assert len(h2) >= 2
        assert any(item["new_status"] == "paid" for item in h2)
