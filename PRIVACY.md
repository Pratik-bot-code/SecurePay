# SecurePay Privacy Policy & Data Minimization Charter

## 1. Core Commitment: Privacy by Design

SecurePay is engineered around strict **Data Minimization** and **Zero-Knowledge** principles for sensitive banking and payment credentials. We believe users should maintain absolute control and visibility over their personal data.

---

## 2. Non-Collection of Sensitive Financial Credentials (Zero-Storage Policy)

SecurePay **never requests, transmits, or stores**:
- ❌ **UPI PINs or ATM PINs:** UPI PIN entry is strictly restricted to secure NPCI-approved bank payment handles and is never handled by SecurePay.
- ❌ **Card CVV / CVC Numbers:** Security codes are never collected or stored.
- ❌ **One-Time Passwords (OTPs):** SecurePay does not intercept or persist bank or SMS authentication codes.
- ❌ **Biometric Raw Data:** Biometric preferences (e.g. FaceID / fingerprint toggles) remain purely local to your device browser settings; biometric templates never touch our servers.
- ❌ **Government IDs or Bank Passwords:** We do not request Aadhaar, PAN, SSN, or online banking passwords.

---

## 3. Data We Collect & Why

| Category | Specific Elements | Purpose | Lawful Basis |
|---|---|---|---|
| Account Credentials | Display Name, Profile Handle (`demo_handle`), Argon2id Password Hash | Account creation, authentication, identification | Performance of contract |
| Session Security | SHA-256 Session Token Hash, HMAC CSRF Token Hash, IP Address (rate limits only) | Session management, CSRF defense, brute-force mitigation | Legitimate interest (security) |
| Transaction Metadata | Reference ID, Amount in Paise, Category, Status, Timestamp | Maintaining double-entry account ledger | Performance of contract |
| Security Audit Trail | Event type (login, registration, failure), Correlation ID, Timestamp | Detecting suspicious logins, fraud prevention, security logging | Legal obligation & security |

---

## 4. No Third-Party Tracking or Advertising

- **Zero Advertising SDKs:** SecurePay contains no marketing pixels, trackers, or advertising beacons.
- **Zero Third-Party Analytics:** We do not sell, rent, or share user behavioral telemetry with external brokers or analytics vendors.
- **Essential Cookies Only:** The only cookie utilized is the secure, HttpOnly session cookie (`securepay_session`) strictly required for authentication.

---

## 5. Data Retention & Erasure

- **Session Data:** Expired or revoked sessions are automatically invalidated and purged according to retention schedules.
- **Account Deletion:** Users have the right to request full account closure and erasure of profile data. Fictional demo ledgers are detached from personal identities upon account closure.
- **Audit Logs:** Security audit events are retained for security analysis and incident response for a rolling window of 90 days.

---

## 6. User Rights

You maintain the following rights regarding your data in SecurePay:
1. **Right to Access & Review:** View all profile information, security sessions, and transaction history in real time from your dashboard.
2. **Right to Session Revocation:** Inspect all connected devices and revoke any active session immediately from the Security settings.
3. **Right to Correction:** Update your display name and preferences at any time.
4. **Right to Data Portability:** Export your transaction history and account details upon request.
