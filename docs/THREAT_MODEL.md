# SecurePay threat model

## Scope and security posture

SecurePay is a web demonstration with fictional users and simulated balances. It does not initiate real UPI, bank, card, or provider payments. The threat model covers the browser, FastAPI service, database, optional rate-limit store, and optional recovery mail adapter. It is a design aid, not a penetration test or assurance that the application is secure.

Security verification is planned against OWASP ASVS 5.0.0 Level 2 as a baseline suitable for an application handling authentication and simulated financial workflows. This is not a claim of ASVS conformance or certification. Map concrete requirements to the selected release during implementation and record evidence and exceptions.

## Assets

| Asset | Security need |
|---|---|
| User passwords and password hashes | Passwords never persisted/logged; hashes protected from disclosure and offline guessing |
| Session cookies and reset tokens | Confidentiality, high entropy, expiry, revocation, single use for reset |
| User profile and account records | Confidentiality, integrity, owner-only access |
| Demo balances and ledger | Atomicity, integrity, accurate presentation as simulated money |
| Idempotency keys and transfer results | Duplicate prevention, user/operation scoping, consistent retries |
| Roles and admin audit data | Least privilege, integrity, restricted access, accountability |
| Application secrets and DB credentials | Confidentiality, rotation, environment/secret-manager storage |
| Service availability | Reasonable resistance to brute force, oversized requests, and abuse |

## Actors and trust boundaries

- Unauthenticated visitor, registered demo user, and explicitly authorized administrator.
- Browser: fully untrusted input and execution environment; users can modify requests and UI state.
- API: trusted policy enforcement point, but vulnerable to flawed authorization, validation, or transaction logic.
- Database and rate-limit service: separate service boundaries requiring restricted credentials/network access.
- Recovery mail provider, if configured: receives sensitive reset links and must be explicitly trusted.
- Future payment provider: outside the current product scope and inactive; no real credentials or live integration.

## Threats and mitigations

| Threat | Example attack/impact | Planned mitigations | Residual risk |
|---|---|---|---|
| Credential stuffing / brute force | Automated login guesses; account takeover | Argon2id, rate limits shared across workers, generic login errors, throttling/progressive delay, security audit events | Rate-limit bypass via distributed sources; operational tuning and monitoring required |
| Account enumeration | Different login/recovery responses reveal valid handles | Generic responses and similar timing, rate limits; avoid exposing recovery delivery state | Timing and side channels require testing |
| Session theft or fixation | Stolen/reused session accesses account | High-entropy opaque session ID, store only hash, Secure/HttpOnly/SameSite cookie, session regeneration, expiry/revocation, HTTPS | Endpoint compromise or browser malware can still expose active sessions |
| CSRF | Cross-site request changes account or submits transfer | SameSite cookie, session-bound CSRF token in custom header, origin checks, explicit CORS allowlist | Misconfigured reverse proxy/origin checks can weaken protections |
| XSS | Injected script steals data or issues authenticated actions | React escaping, no unsafe HTML by default, input validation, reviewed CSP/security headers, dependency hygiene | XSS can act as the user in the browser; manual review remains necessary |
| IDOR / broken access control | User reads another profile, transaction, receipt, or session | Derive user from session, scope every query by owner, backend role checks, negative authorization tests | New endpoints can regress; enforce review/test coverage for every protected route |
| Mass assignment / privilege escalation | Client changes role, account owner, balance, or status | Explicit Pydantic request/response schemas; server-owned fields set only by domain services; never trust client roles/balances/status | Schema drift and unsafe ORM binding remain review risks |
| Duplicate transfer / replay | Retries or parallel duplicate requests debit twice | Unique user+operation+idempotency key, canonical request fingerprint, atomic key claim, original result on valid retry | Key retention/expiry and race handling need PostgreSQL integration tests |
| Concurrent overspending | Simultaneous transfers exceed available balance | PostgreSQL row locks or conditional atomic debit; consistent lock order; DB transaction and balance constraints | SQLite cannot validate production locking behavior; load testing required |
| Partial debit/credit or ledger tampering | Failure between account updates leaves inconsistent balance | One atomic DB transaction; double-entry integer-paise ledger; constraints; append-only runtime DB permissions/trigger; integrity tests | Database owner/host compromise can bypass runtime permissions; operational controls needed |
| SQL injection | Malicious input changes database query | SQLAlchemy parameterized queries, no string-built SQL, input constraints, least privilege | Raw SQL additions require focused review |
| Sensitive-data leakage | Errors/logs/responses expose passwords, tokens, secrets, or request bodies | Response allowlists, safe exception handling, metadata-only logs, secret redaction, tests for exposure | Third-party infrastructure logs and crash dumps need independent configuration review |
| Denial of service / resource abuse | Large request bodies, costly validation, notification/API flooding | Body/field limits, rate limits, timeouts, bounded queries/pagination, reverse-proxy limits | Capacity depends on deployment; load and abuse tests required |
| Malicious or weak recovery flow | Reset token exposed or reused to take over account | High-entropy short-lived token; store hash only; generic responses; atomic one-time use; optional configured mail adapter | Mailbox compromise and provider misconfiguration remain risks |
| Cross-origin data exposure | Untrusted origin reads credentialed API responses | Explicit origin allowlist; no wildcard with credentials; same-site production topology | Deployment origin drift must be checked at release |
| Admin audit misuse | Admin accesses secrets or unnecessary personal data | Backend RBAC, read-only/minimized dashboard, audit sensitive admin access/actions, never expose auth secrets | Admin account compromise and insider risk remain |
| Dependency/supply-chain compromise | Vulnerable or malicious package compromises app | Pin tested dependencies, vulnerability checks, review upgrades and lockfiles, minimize dependency set | Scanners miss unknown vulnerabilities; maintainers and build pipeline remain trusted |
| Demo confusion / financial deception | User mistakes simulated receipt for real payment | Persistent DEMO marking, fictional users, conspicuous simulated status on every transaction/receipt; no provider connection | Screenshots or downstream reuse may omit context; include labels in exported receipts |

## Privacy controls and data minimization

- Collect only synthetic demo handle, password, fictional display name, demo transaction details, and security metadata needed for the feature.
- Do not collect bank credentials, UPI PINs, card CVVs, OTPs, government ID numbers, contacts, SMS, location, or device fingerprints.
- Do not use analytics or third-party tracking by default.
- Avoid storing raw session and reset tokens; do not log secrets, full request bodies, or unnecessary personal data.
- Provide a privacy notice describing collected data, purpose, retention, deletion/anonymization, and demo limitations.
- Apply owner-scoped access and delete/revoke associated data according to documented retention rules. Clarify any ledger retention/anonymization exception.

## ASVS verification plan

Use ASVS 5.0.0 Level 2 as a checklist baseline for:

- Architecture, threat modeling, secure configuration, and error handling.
- Authentication, credential storage, recovery, and session management.
- Authorization, ownership checks, and role enforcement.
- Input validation, injection prevention, output encoding, and browser security.
- API communication, CORS, CSRF, TLS, and security headers.
- Cryptography and sensitive data protection.
- Secure logging, audit access, and operational configuration.
- Business logic, transaction integrity, replay/idempotency, and abuse resistance.

During implementation, map each applicable control to code/test/configuration evidence and mark controls not applicable with a reason. Do not infer compliance from tests alone.

## Required manual review and residual checks

- Review cookie, CSRF, CORS, CSP, TLS termination, and proxy/header behavior in the actual deployment topology.
- Review PostgreSQL isolation/locking, migrations, ledger constraints/append-only protections, runtime DB privileges, and backup/restore behavior.
- Review recovery-email configuration, token delivery, expiry, and anti-enumeration behavior.
- Review dependency advisories, build provenance, secret management, logging/redaction, monitoring, and incident response.
- Perform manual authorization/IDOR and browser security testing across all routes and UI flows.
- Conduct an independent professional penetration test before any production use or real-provider integration.
- Reassess compliance, privacy, legal, and provider requirements before expanding beyond fictional demo money.
