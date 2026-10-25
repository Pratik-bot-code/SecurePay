# Security Controls Status

## Scope

This is an implementation-status report for the SecurePay account dashboard, not a certification or a full independent penetration test. SecurePay has no bank, UPI, SMS, biller, or real-money provider integration. Payment endpoints are disabled until a provider is approved and integrated.

## Implemented and regression-tested controls

| Area | Current control | Evidence |
|---|---|---|
| Authentication | Argon2 password hashing, opaque HttpOnly session cookies, secure production cookie requirement, login/register throttles, session-bound CSRF | `backend/app/core/security.py`, `backend/app/api/routes.py`, backend test suite |
| Payment approval | Transfers return HTTP 503 until an approved provider is integrated; no payment is initiated by the app | `backend/app/api/routes.py`, `test_payment_routes_stay_unavailable_without_provider` |
| Authorization | Owner-scoped profile, notification, and session access; financial history endpoints expose no records while no provider is connected | `backend/app/api/routes.py`, ownership tests |
| Duplicate payments | No payment operation is exposed, so payment idempotency is not active | `backend/app/api/routes.py` |
| Fraud/velocity controls | No payment operation is exposed; provider-specific risk controls remain a prerequisite | Provider integration not available |
| Audit/monitoring | Sensitive events persisted in the security audit table; denied, rate-limited, velocity-limited, and unavailable controls emit structured security log records; responses include generated request IDs | `backend/app/core/security.py`, `backend/app/main.py` |
| Recovery | Recovery endpoint fails closed with HTTP 503 and an audit record while no verified contact/recovery provider exists | Recovery regression test |
| Production transport | Production startup requires secure cookies and PostgreSQL configured with `sslmode=verify-full`; HSTS is emitted in production | `backend/app/core/config.py`, `backend/app/main.py`, configuration test |

The app does not collect, send, or store UPI PINs. No regulated payment authorization or provider-backed payment challenge is implemented.

## Verification performed

- Backend: `backend\.venv\Scripts\python.exe -m pytest` — 8 passed; one upstream Starlette/httpx deprecation warning.
- Database: `python -m alembic check` — no schema drift detected; no migration was required by these changes.
- Frontend: `npm run build` — passed.
- Browser: verified the dashboard's provider-unavailable message, the absence of generated receive QR codes and sample transaction rows, and the receive page at 390px with no horizontal overflow.
- PostgreSQL TLS connection, PostgreSQL-specific migrations/locking, real SMS/OTP, external monitoring, production database permissions, and storage/backup encryption were not exercised.

## Not implemented: provider or hosting requirements

- **Verified mobile number/OTP:** no SMS provider is configured. Accounts are not phone-verified; do not treat this app as real-world account authentication.
- **Cryptographic device binding:** active server sessions can be listed and revoked, but browser sessions are not bound to hardware keys/passkeys.
- **Real-payment approval:** no payment network/provider is integrated; outgoing transfers are intentionally blocked.
- **At-rest encryption and encrypted backups:** require deployment/database/storage-provider configuration. The local SQLite database is not encrypted by this application.
- **Least-privilege database credentials:** must be provisioned and restricted by the deployment operator; the app cannot reduce privileges of an externally supplied database user.
- **External alerting and incident response:** events reach application logs and in-app notices only. No SIEM, paging, response runbook, or on-call service is connected.
- **Production operations:** PostgreSQL migrations and concurrent transfer behavior have not been exercised here. SQLite does not provide equivalent row-lock concurrency guarantees.

Do not deploy this application as a banking or payment service. Select and configure the phone-verification, recovery, device-authentication, payment, database, backup, and monitoring providers before treating those controls as available.
