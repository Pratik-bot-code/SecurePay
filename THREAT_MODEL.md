# SecurePay Threat Model & STRIDE Analysis

## 1. Scope & System Architecture

SecurePay is a digital payment web application prototype modeled on modern payment systems (e.g. UPI, QR, peer-to-peer transfers). The architecture comprises:
- **Client Tier:** React / Vite Single Page Application running in untrusted end-user browsers.
- **API Tier:** FastAPI (Python 3.11+) acting as the Policy Enforcement Point (PEP) and Policy Decision Point (PDP).
- **Data Tier:** Relational database (SQLite for local development, PostgreSQL for production) enforcing foreign keys, unique constraints, and trigger-enforced ledger immutability.
- **Provider Gateway (Future Phase 4):** Authorized Indian payment provider sandbox (e.g., Razorpay/Cashfree) communicating via signed server-to-server webhooks and order APIs.

---

## 2. Asset Classification & Security Objectives

| Asset | Sensitivity | Confidentiality | Integrity | Availability | Security Controls |
|---|---|---|---|---|---|
| User Passwords | Critical | Must never be revealed | Cannot be tampered | High | Argon2id, strict strength rules, zero plaintext persistence |
| Session & CSRF Tokens | High | Protected from theft | Bound to session ID | High | HttpOnly cookies, SHA-256 token hashing, HMAC-SHA256 CSRF |
| Ledger & Balances | High | Owner-visible only | Double-entry, DB trigger immutable | High | Integer paise math, atomic transactions, trigger locks |
| Audit Trail | High | Restricted access | Append-only audit table | High | Correlated request IDs, immutable records |
| Application Secrets | Critical | Kept backend-only | Strict env configuration | High | Min 32-char secret, production validation guards |

---

## 3. STRIDE Threat Analysis

### S — Spoofing
- **Threat:** Attacker impersonates an existing user or sends counterfeit session tokens.
- **Mitigation:**
  - High-entropy session IDs (`secrets.token_urlsafe(32)`).
  - Only SHA-256 hashes stored on the server.
  - Active session validation requiring both cookie and CSRF token match.
  - Constant-time verification (`hmac.compare_digest`).

### T — Tampering
- **Threat:** Attacker modifies account balances, ledger entries, or transaction payloads in flight.
- **Mitigation:**
  - Balances calculated exclusively by server-side double-entry ledger logic.
  - DB triggers on `ledger_entries` forbid `UPDATE` and `DELETE` operations at the database engine level.
  - Pydantic models strictly validate and sanitize input fields.
  - Idempotency key fingerprinting prevents replay tampering.

### R — Repudiation
- **Threat:** User or attacker denies performing a sensitive account or financial action.
- **Mitigation:**
  - Comprehensive `audit_events` logging recording `user_id`, `event_type`, `outcome`, `timestamp`, and `correlation_id`.
  - Immutable ledger rows tied to specific `transaction_id` and timestamped in UTC.

### I — Information Disclosure
- **Threat:** Sensitive user data, session IDs, or internal errors leaked via HTTP responses, headers, or logs.
- **Mitigation:**
  - Responses serialized via strict Pydantic schemas (passwords, hashes, and internal keys excluded).
  - Unhandled exceptions return generic messages (`"The request could not be completed."`).
  - Strict security headers (`nosniff`, `DENY`, `no-referrer`, restrictive CSP).
  - Credentials and tokens redacted from all application logs.

### D — Denial of Service
- **Threat:** Attacker floods authentication endpoints or submits oversized payloads to exhaust server memory.
- **Mitigation:**
  - Global 64KB request body limit middleware.
  - Sliding-window database-backed rate limiting per IP host and profile handle on registration and login.
  - Database connection pooling with pre-ping validation.

### E — Elevation of Privilege
- **Threat:** Regular user assumes administrator privileges or modifies other users' data (IDOR).
- **Mitigation:**
  - User identity strictly derived from the validated server session (`AuthContext.user`).
  - No client-controlled role or permission parameters.
  - Negative authorization regression tests covering all private routes.

---

## 4. Trust Boundaries

```
[ Untrusted Client: Browser / Attacker ]
               │
               ▼  (HTTPS / TLS 1.3, Strict CORS, 64KB Limit, Rate Limiter)
[ Boundary 1: Edge & FastAPI Middleware ]
               │
               ▼  (Session Token Hash Verification, CSRF HMAC Verification)
[ Boundary 2: Application Core & Services ]
               │
               ▼  (Parameterized Queries, DB Triggers, TLS / sslmode=verify-full)
[ Boundary 3: Database (PostgreSQL / SQLite) ]
```

---

## 5. OWASP ASVS v5.0.0 Level 2 Verification Mapping

- **V1: Architecture:** Threat model documented; security controls centralized in `app.core.security`.
- **V2: Authentication:** Argon2id hashing, 12+ character policy, enumeration-resistant error messages.
- **V3: Session Management:** HttpOnly, SameSite=Lax, SHA-256 session token hashing, active session revocation.
- **V4: Access Control:** All resource access scoped to session owner; IDOR verified by negative tests.
- **V5: Validation & Sanitization:** Strict Pydantic schemas, body size limit, regex pattern matching on handles.
- **V8: Cryptography:** Recommended password algorithms, constant-time comparisons, high-entropy tokens.
- **V14: Configuration:** Production startup assertions for secret length, database TLS, and secure cookies.

---

## 6. Residual Risks & Production Prerequisites

1. **Production Reverse Proxy:** TLS termination and HSTS must be configured at the web server/reverse proxy (Nginx/Cloudflare/Caddy).
2. **Provider Onboarding:** Real money transfers require integration with a licensed payment aggregator (Phase 4).
3. **Database Credentials:** Least-privilege database user permissions must be enforced in production deployments.
