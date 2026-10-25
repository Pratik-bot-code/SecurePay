# SecurePay implementation history

Payment simulations and seed fixtures have been removed from the active application. Transfers remain unavailable until an approved payment provider and the required operational controls are integrated.

## Goal and scope

Build a locally runnable, responsive payment-app demonstration using fictional users and simulated money only. The application must label the product and every simulated payment as **DEMO**. It will not connect to banks, UPI, cards, or payment providers, and will not claim that a real payment has occurred.

This plan began as the Phase 1 design baseline. The project now has a local frontend and FastAPI backend; implementation and verification status is recorded below.

## Workspace assessment

The workspace was empty at the start of Phase 1. There is no existing code, dependency manifest, test suite, or framework convention to retain. The design follows the requested React/Vite and FastAPI stack and favors a small local setup.

## Decisions and assumptions

| Topic | Phase 1 decision |
|---|---|
| Frontend | React, Vite, TypeScript, React Router, Lucide icons, responsive CSS |
| Backend | Python FastAPI, Pydantic validation, SQLAlchemy ORM, Alembic migrations |
| Persistent data | PostgreSQL for the documented primary setup; SQLite may be supported for lightweight local development, but is not an equivalent test of PostgreSQL concurrency or locking |
| Sessions | Opaque, high-entropy server-side sessions; only a hash of the cookie value is persisted |
| Browser authentication | `Secure`, `HttpOnly`, `SameSite` session cookie in production; CSRF token required for state-changing cookie-authenticated requests; no auth tokens in localStorage |
| Passwords | Argon2id via a maintained password-hashing library |
| Rate limiting | Shared rate-limit storage in multi-worker/production setups; per-process memory alone is insufficient |
| Transfers | Integer paise, double-entry ledger, atomic database transaction, idempotency key, and server-derived sender/account |
| Provider integration | Provider interface only; no live adapter, credentials, network calls, or real-money path |
| Demo accounts | Synthetic seed data for local development only; no default production administrator |
| Recovery | Generic responses and hashed, expiring, single-use reset tokens; no reset token in logs or API responses. Delivery must use an explicitly configured mail adapter; otherwise the interface must clearly explain that recovery delivery is unavailable in the local demo |
| Deployment | Local development is in scope. Production deployment is not; HTTPS, secret management, database privileges, backups, monitoring, and operational review remain prerequisites |
| Security target | Use OWASP ASVS 5.0.0 Level 2 as a planning and verification baseline, not as a certification or claim of security |

## Work plan

### Phase 1 — Inspect and design (current)

- Inspect the workspace and record the starting state.
- Define the architecture, trust boundaries, data ownership, data model, payment invariants, and threat model.
- Record remaining assumptions and security limitations.
- Artifacts: this plan, [ARCHITECTURE.md](./ARCHITECTURE.md), [DATA_MODEL.md](./DATA_MODEL.md), and [THREAT_MODEL.md](./THREAT_MODEL.md).

### Phase 2 — Frontend shell and requested demo flows — implemented

- Implemented the responsive dashboard, authenticated send/receive flows, QR generation/manual demo-ID entry, transaction history/search/filters/export, receipts, profile, security preferences/session management, and notifications.
- Added registration/login and a generic recovery-request screen. Recovery delivery remains unconfigured.
- Connected state-changing and owner-scoped UI flows to the FastAPI backend; the browser smoke test completed registration and a simulated transfer/receipt.
- Recharge/bill screens, help/legal pages, admin audit dashboard, and automated frontend test coverage remain out of scope.

### Phase 3 — Backend foundation, persistence, and identity — implemented with recovery limitation

- Added FastAPI, settings validation, SQLAlchemy models, Alembic migrations, and PostgreSQL/SQLite database configuration. Startup now requires an applied Alembic revision; it does not call `create_all`.
- Implemented registration, login/logout, server-side sessions, session revocation, password changes, owner-scoped endpoints, CSRF/origin checks, and audit events.
- Added Argon2id password hashing, request validation, generic authentication/recovery responses, database-backed rate-limit buckets, and security response headers.
- Recovery request responses are generic, but token delivery and password reset are not implemented.
- SQLite API tests verify CSRF, logout, cross-user transaction/notification/session access denial, profile isolation, and ledger behavior. Expiration, rate-limit thresholds, and sensitive-data logging need additional test coverage.

### Phase 4 — Simulated ledger and payment workflows — implemented; PostgreSQL verification pending

- Implemented integer-paise simulated transfers, server-derived sender/account ownership, synthetic-recipient restrictions, balance checks, paired ledger entries, audit notifications, and idempotency.
- Database operations update balances, transaction records, ledger entries, and idempotency outcomes in a single unit of work.
- PostgreSQL uses ordered account row locks and has database trigger definitions for immutable/balanced ledger entries. SQLite immutability is verified; PostgreSQL behavior and concurrent transfers were not exercised.
- Earlier tests covered replayed idempotency keys, insufficient funds, unchanged balances on cross-user transfer attempts, balanced ledger entries, immutable SQLite ledger rows, and simulated receipt behavior. These payment flows have since been disabled; current tests verify fail-closed behavior without a provider.

### Phase 5 — Frontend/API integration — implemented

- Added a credentialed API client with in-memory CSRF handling and a Vite API proxy.
- Dashboard, transactions/details, payment, QR/demo-ID receive, profile, preferences, sessions, notifications, password change, and sign-out use backend endpoints. Receipts appear only after a committed backend response.
- Cross-user ownership, CSRF, and key payment flows were verified with API tests and a browser smoke test; authentication-expiry UX and broader error scenarios need more coverage.

### Phase 6 — Synthetic data and local development — implemented

- Added synthetic directory users, demo funding accounts, and a double-entry opening pool. No seed credentials are available for directory users.
- Added PostgreSQL Docker Compose configuration, placeholder environment settings, ignored local data, and local setup instructions in the root README.
- Production mode rejects default secrets, insecure cookies, wildcard CORS, demo seeding, and SQLite.

### Phase 7 — Verification and security checks — partial

- Backend: `pytest` passes 5 API tests; `alembic upgrade head` and `alembic check` pass on a fresh SQLite database.
- Frontend: `npm run build` succeeds; a live browser smoke test registered a user and completed a simulated payment with a backend receipt.
- PostgreSQL migration/trigger/locking tests, broader rollback/rate-limit/expiry tests, frontend automated tests, and final dependency audit remain outstanding.

### Phase 8 — Documentation and handoff — implemented with known limitations

- Added local setup/test instructions and documented demo-only capability, recovery limitations, and PostgreSQL validation gaps.
- Independent security review and production readiness work remain out of scope.

## Acceptance checklist

- [x] Documented local setup is available; a full clean-checkout setup has not been exercised.
- [ ] Alembic migrations apply to PostgreSQL; the SQLite migration path is tested separately.
- [x] Frontend production build succeeds.
- [x] Backend starts with generic API errors and debug details disabled by default.
- [x] Registration, logout, and protected ownership checks pass focused tests; session revocation is owner-scoped.
- [x] Key UI flows function and clearly identify demo money and demo transactions.
- [ ] Transfer atomicity, idempotency, concurrency, rollback, sufficient-funds checks, and ledger invariants are tested.
- [ ] No real payment provider or financial credentials are requested or used.
- [ ] No secrets or sensitive authentication material appear in browser storage, responses, logs, or committed files.
- [ ] Automated tests and dependency checks are run; limitations and manual review needs are documented.

## Risks and sequencing notes

- PostgreSQL-specific row locking, constraints, and append-only protections must be tested against PostgreSQL. SQLite is a convenience option, not evidence of equivalent concurrency safety.
- Browser cookie authentication needs a coherent origin/deployment setup. Production should serve the frontend and API same-site (preferably same-origin behind a reverse proxy) and use HTTPS.
- Email delivery for password recovery is not available by default. A real delivery provider requires explicit configuration and separate review; a token must never be exposed as a convenient demo shortcut.
- Admin screens are useful only after server-side role checks and synthetic local-only admin provisioning are in place.
- This is a demonstration, not a production banking application or a substitute for independent security assessment.
