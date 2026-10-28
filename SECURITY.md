# Security Policy and Architecture — SecurePay

## Overview

SecurePay is designed with a defense-in-depth, zero-trust security architecture inspired by modern digital banking standards. While operating in a demonstration/sandbox mode, the application rigorously enforces market-grade application security controls, cryptographic safeguards, and strict data minimization.

---

## 1. Cryptographic Controls & Password Hashing

- **Password Hashing:** Passwords are hashed exclusively using the **Argon2id** algorithm via `pwdlib` (`PasswordHash.recommended()`). Plaintext passwords are never logged, persisted, or returned in API responses.
- **Password Strength Policy:** Passwords must be between 12 and 128 characters, reject common dictionary passwords, forbid purely numeric strings, forbid repeated characters, and require a mix of character varieties.
- **Session Tokens:** Sessions are generated using cryptographically secure pseudorandom numbers (`secrets.token_urlsafe(32)`, providing ~256 bits of entropy).
- **Session Hashing:** Only the SHA-256 hash of the session token is stored in the database (`server_sessions.session_token_hash`). Compromise of the database does not reveal valid browser session tokens.
- **CSRF Token Generation:** CSRF tokens are derived using HMAC-SHA256 keyed with the application's `SESSION_SECRET` bound to the unique session ID (`hmac(secret, "securepay-csrf:<session_id>")`).

---

## 2. Authentication & Session Management

- **HttpOnly Cookies:** Session tokens are delivered solely via `HttpOnly`, `SameSite=Lax` cookies, preventing direct JavaScript access and mitigating cross-site scripting (XSS) session theft.
- **Production Transport Security:** In production mode (`ENVIRONMENT=production`), the application strictly enforces:
  - `session_cookie_secure = True` (cookies only sent over HTTPS).
  - PostgreSQL database connection with `sslmode=verify-full`.
  - HTTP Strict Transport Security (`Strict-Transport-Security: max-age=31536000; includeSubDomains`).
- **Session Activity Tracking:** Authenticated requests automatically update the session's `last_seen_at` timestamp.
- **Explicit Revocation & Invalidation:**
  - Users can view all active sessions and revoke individual remote sessions.
  - Changing the account password automatically rotates the current session and revokes all other active sessions for that user.
  - Logging out immediately invalidates the server-side session and clears the browser cookie.

---

## 3. Authorization & IDOR Defenses

- **Owner-Scoped Queries:** All API queries for profiles, notifications, transactions, and session management are derived directly from the authenticated session context (`AuthContext.user.id`).
- **No Client-Supplied Identifiers for Sensitive Actions:** Endpoints do not accept arbitrary user IDs in request payloads to access private records.
- **Negative Authorization Verification:** The automated test suite (`test_api_ownership.py` and `test_security_hardening.py`) verifies that User A cannot read, modify, or revoke User B's sessions, notifications, or preferences.
- **Mass-Assignment Protection:** Strict Pydantic models define validated incoming schemas. Server-side attributes (`role`, `status`, `balance_paise`) cannot be modified by user input.

---

## 4. Cross-Site Request Forgery (CSRF) & Origin Defense

- **Double-Defense Architecture:**
  1. **SameSite Cookie Policy:** Browser cookies use `SameSite=Lax`.
  2. **Session-Bound CSRF Tokens:** State-changing requests (POST, PUT, PATCH, DELETE) require the `X-CSRF-Token` header. The token is validated using constant-time HMAC comparison against the session's stored hash.
  3. **Origin & CORS Verification:** Requests containing an `Origin` header are checked against the explicit `CORS_ORIGINS` allowlist. Wildcard origins (`*`) are prohibited when credentials are enabled.

---

## 5. Rate Limiting & Denial of Service (DoS) Protections

- **Sliding-Window Rate Limiting:** Built-in rate limiting per IP host and account handle:
  - Account registration: 5 requests / minute / IP (configurable).
  - Account login: 10 requests / minute / IP (configurable).
- **Request Body Limits:** A global middleware rejects request bodies exceeding 64KB with `HTTP 413 Payload Too Large`.
- **Database Dialect Support:** Rate limit buckets utilize atomic UPSERT statements (`ON CONFLICT DO UPDATE` for PostgreSQL and SQLite) to prevent race conditions across concurrent workers.

---

## 6. Audit Logging & Observability

- **Structured Security Auditing:** Critical events (failed logins, registration denials, password rotations, rate-limiting triggers, authorization denials) are persisted in the `audit_events` table.
- **Correlation IDs:** Every request receives a cryptographically generated Request ID (`X-Request-ID`) which is returned in headers and tagged on audit logs.
- **Zero Sensitive Data Logging:** Plaintext passwords, tokens, full request bodies, or payment details are never recorded in log files or audit tables.

---

## 7. Security Headers

The application sets strict HTTP response headers on every response:
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'
```
*(Interactive API documentation routes at `/api/docs` and `/api/redoc` specify scoped script/style directives for OpenAPI UI assets).*

---

## 8. Responsible Disclosure & Vulnerability Reporting

If you discover a security vulnerability in SecurePay:
1. **Do not create public GitHub issues** for suspected security vulnerabilities.
2. Report the vulnerability privately to the project security maintainers at `security@securepay.local` (or via private security advisory).
3. Include:
   - Description of the vulnerability.
   - Steps to reproduce or proof-of-concept.
   - Potential impact.
4. Maintainers will acknowledge reports within 48 hours and coordinate remediation before public disclosure.
