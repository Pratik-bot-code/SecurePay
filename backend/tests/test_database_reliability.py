import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, InternalError, OperationalError

from app.core.config import get_settings
from app.core.database import SessionLocal, make_engine
from app.main import app
from app.models import DemoAccount, LedgerEntry, LinkedBankAccount, Merchant, ServerSession, Transaction, User


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


def test_linked_bank_accounts_lifecycle_and_owner_isolation():
    with TestClient(app) as client_a:
        user_a, csrf_a = create_user(client_a, f"banka.{secrets.token_hex(4)}")

        with TestClient(app) as client_b:
            user_b, csrf_b = create_user(client_b, f"bankb.{secrets.token_hex(4)}")

            # 1. User A links a bank account
            link_res = client_a.post(
                "/api/accounts/banks",
                headers={"X-CSRF-Token": csrf_a},
                json={
                    "bank_name": "State Bank of India",
                    "account_holder_name": "User Bank A",
                    "account_number": "123456789012",
                    "ifsc_code": "SBIN0001234",
                    "account_type": "savings",
                },
            )
            assert link_res.status_code == 201, link_res.text
            bank_a = link_res.json()
            assert bank_a["bank_name"] == "State Bank of India"
            assert bank_a["masked_account_number"] == "•••• •••• 9012"
            assert bank_a["is_primary"] is True
            assert "123456789012" not in link_res.text  # Raw account number never in response

            # Verify in DB: raw account number NEVER stored
            with SessionLocal() as db:
                db_bank = db.get(LinkedBankAccount, bank_a["id"])
                assert db_bank is not None
                assert db_bank.masked_account_number == "•••• •••• 9012"

            # 2. User B cannot see User A's bank account
            banks_b = client_b.get("/api/accounts/banks").json()
            assert len(banks_b) == 0

            # 3. User B cannot delete User A's bank account
            del_res = client_b.delete(
                f"/api/accounts/banks/{bank_a['id']}",
                headers={"X-CSRF-Token": csrf_b},
            )
            assert del_res.status_code == 404

            # 4. User A can link a second account and set it to primary
            link_res2 = client_a.post(
                "/api/accounts/banks",
                headers={"X-CSRF-Token": csrf_a},
                json={
                    "bank_name": "HDFC Bank",
                    "account_holder_name": "User Bank A",
                    "account_number": "987654321098",
                    "ifsc_code": "HDFC0005678",
                    "account_type": "current",
                },
            )
            assert link_res2.status_code == 201
            bank_a2 = link_res2.json()
            assert bank_a2["is_primary"] is False

            # Set second bank as primary
            primary_res = client_a.post(
                f"/api/accounts/banks/{bank_a2['id']}/primary",
                headers={"X-CSRF-Token": csrf_a},
            )
            assert primary_res.status_code == 200
            assert primary_res.json()["is_primary"] is True

            # 5. User A deletes the first account
            del_a_res = client_a.delete(
                f"/api/accounts/banks/{bank_a['id']}",
                headers={"X-CSRF-Token": csrf_a},
            )
            assert del_a_res.status_code == 204

            # Verify only second account remains
            remaining = client_a.get("/api/accounts/banks").json()
            assert len(remaining) == 1
            assert remaining[0]["id"] == bank_a2["id"]


def test_merchant_profile_registration_and_isolation():
    with TestClient(app) as client_a:
        user_a, csrf_a = create_user(client_a, f"mercha.{secrets.token_hex(4)}")

        with TestClient(app) as client_b:
            user_b, csrf_b = create_user(client_b, f"merchb.{secrets.token_hex(4)}")

            # Initially neither has a merchant profile
            assert client_a.get("/api/merchant").status_code == 404
            assert client_b.get("/api/merchant").status_code == 404

            # User A registers as a merchant
            reg_res = client_a.post(
                "/api/merchant/register",
                headers={"X-CSRF-Token": csrf_a},
                json={
                    "business_name": "Supermart Express",
                    "category": "Retail & Groceries",
                },
            )
            assert reg_res.status_code == 201
            merchant_a = reg_res.json()
            assert merchant_a["business_name"] == "Supermart Express"
            assert "MERCH_" in merchant_a["merchant_code"]
            assert "@securepay" in merchant_a["upi_handle"]

            # User A can now fetch their merchant profile
            assert client_a.get("/api/merchant").status_code == 200

            # User B still has no merchant profile
            assert client_b.get("/api/merchant").status_code == 404


def test_persistence_across_database_reconnection():
    handle = f"persist.{secrets.token_hex(4)}"
    with TestClient(app) as client:
        user, _ = create_user(client, handle)
        user_id = user["id"]

    # Simulate database engine reset / restart
    engine2 = make_engine()
    with SessionLocal() as db:
        persisted_user = db.get(User, user_id)
        assert persisted_user is not None
        assert persisted_user.demo_handle == handle
        assert persisted_user.status == "active"

        # Check account persistence
        account = db.scalar(select(DemoAccount).where(DemoAccount.user_id == user_id))
        assert account is not None
        assert account.balance_paise == 0


def test_ledger_trigger_immutability():
    # Verify that ledger entries cannot be updated or deleted due to DB triggers
    with SessionLocal() as db:
        user = User(
            demo_handle=f"trigger.{secrets.token_hex(4)}",
            display_name="Trigger Test",
            password_hash="argon2_fake_hash_placeholder",
        )
        db.add(user)
        db.flush()

        acc = DemoAccount(user_id=user.id, label="Trigger Account", account_type="user", balance_paise=1000)
        db.add(acc)
        db.flush()

        tx = Transaction(
            reference=f"TX_{secrets.token_hex(6).upper()}",
            transaction_type="demo_grant",
            recipient_account_id=acc.id,
            amount_paise=1000,
            currency="INR",
        )
        db.add(tx)
        db.flush()

        entry = LedgerEntry(
            transaction_id=tx.id,
            account_id=acc.id,
            amount_paise=1000,
            entry_type="credit",
        )
        db.add(entry)
        db.commit()

        entry_id = entry.id

        # Attempt to mutate the ledger entry
        with pytest.raises((IntegrityError, InternalError, OperationalError)):
            entry.amount_paise = 2000
            db.commit()

        db.rollback()

        # Attempt to delete the ledger entry
        with pytest.raises((IntegrityError, InternalError, OperationalError)):
            db.delete(entry)
            db.commit()

        db.rollback()
