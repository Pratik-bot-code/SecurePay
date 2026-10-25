# SecurePay data model

Implementation note: the current SQLAlchemy schema keeps display name and security preferences on `users` rather than a separate `user_profiles` table. `is_directory` distinguishes synthetic payment recipients from registered account holders. The local demo seeds non-login directory entries and a funding pool.

## Conventions

- Use UUID primary keys, UTC timestamps, foreign keys, database constraints, and indexes for ownership and common lookup paths.
- Store monetary values as signed integer paise. Reject non-positive transfer amounts and values outside configured demo limits.
- Never store real banking, card, UPI PIN, OTP, government-ID, contact, location, or device-fingerprint data.
- User-visible handles are synthetic demo identifiers, unique after a documented normalization rule.
- Persist only password hashes, hashes of session/reset secrets, and minimum metadata required by the feature.
- The authenticated user is derived from the session, not a request's user/account ID.

## Entities

### `users`

- `id` (UUID, primary key)
- `demo_handle` (normalized, unique, not null)
- `password_hash` (Argon2id output, not null)
- `role` (constrained enum/value, default `user`)
- `status` (active/disabled)
- `is_directory` (synthetic recipient, never login-enabled)
- `biometric_preference`, `security_alerts`
- `created_at`, `updated_at`

Do not return `password_hash` in API schemas. Administrator provisioning is local-only synthetic setup; never seed production with a default administrator credential.

Display name is also stored on `users`; there is no separate profile table in the current schema. Do not add real identity-document or full contact fields for the demo.

### `demo_accounts`

- `id` (UUID, primary key)
- `user_id` (nullable FK to `users`, unique for one user wallet; null for system accounts)
- `account_type` (`user`, `system`, or `system_offset`)
- `currency` (fixed to the demo-supported currency, e.g. `INR`)
- `balance_paise` (integer projection; user/funding accounts are non-negative and the synthetic offset account is non-positive)
- `status` (active/disabled)
- `created_at`, `updated_at`

Balance changes are allowed only in transfer/grant domain operations and must be accompanied by balanced ledger entries in the same database transaction. Never accept balances from the client.

### `transactions`

- `id` (UUID, primary key)
- `reference` (unique, unpredictable or non-sequential public reference)
- `sender_account_id`, `recipient_account_id` (FKs to demo accounts; distinct)
- `amount_paise` (positive integer)
- `currency`
- `transaction_type` (`transfer` or `demo_grant`)
- `category`, optional `note`, synthetic `counterparty_label`/`counterparty_handle` for demo grants
- `status` (`posted` in the current implementation; do not report a transfer as posted before commit)
- `created_at`, `posted_at`

Only posted transfers have monetary ledger entries. Store transition history in `transaction_status_events` if status changes need an auditable trail. Failure records must not imply funds moved; failed attempts and transfer-domain errors do not create partial ledger entries.

### `ledger_entries`

- `id` (UUID, primary key)
- `transaction_id` (FK to `transactions`)
- `account_id` (FK to `demo_accounts`)
- `amount_paise` (signed non-zero integer)
- `entry_type` (debit/credit)
- `created_at`

Each posted transfer creates exactly two entries in its currency: sender debit and recipient credit, whose sum is zero. Enforce uniqueness for one debit and one credit per transaction. The service writes both entries atomically; PostgreSQL also has a deferred balance trigger, while SQLite tests verify that ledger rows cannot be updated or deleted. Application code must not mutate ledger rows.

### `idempotency_records`

- `id` (UUID, primary key)
- `user_id` (FK to `users`)
- `operation` (e.g. `transfer`)
- `key` (opaque client-generated key; unique with user and operation)
- `request_fingerprint` (hash of canonical validated parameters, not secrets)
- `transaction_id` (nullable FK while processing; unique where populated)
- `result_status`, `created_at`, `expires_at`

Reuse with the same fingerprint returns the original result; reuse with different parameters is rejected. Create/claim the key atomically to prevent concurrent duplicate execution. Retention must be long enough to cover retry behavior and documented.

### `server_sessions`

- `id` (UUID primary key)
- `user_id` (FK to `users`)
- `session_token_hash` (unique hash of high-entropy raw cookie value)
- `csrf_token_hash` or equivalent session-bound CSRF verifier
- Minimal `created_at`, `last_seen_at`, `expires_at`, `revoked_at` timestamps

Never persist or log the raw cookie value or CSRF token. Do not collect detailed device identifiers or location. Session listing may expose only a generic session label and timestamps; revocation is by the authenticated owner or authorized administrator.

### `password_reset_requests`

- `id` (UUID primary key)
- `user_id` (nullable FK if generic nonexistent-account handling requires indistinguishable behavior; avoid using it to expose account existence)
- `token_hash` (unique hash of a high-entropy single-use token)
- `created_at`, `expires_at`, `used_at`

Only the hash is stored. Enforce short expiry and one-time use. Do not include token values in API responses or logs. Delivery is disabled until an explicit mail adapter is configured.

### `security_audit_events`

- `id` (UUID primary key)
- `event_type` (constrained category)
- `user_id` (nullable FK when unauthenticated)
- `outcome` (success/denied/failure)
- `occurred_at`
- Minimal optional request correlation ID and coarse operational metadata

Record authentication outcomes, logout/revocation, denied authorization, recovery requests, and demo transfers. Do not store passwords, reset/session tokens, full request bodies, or unnecessary IP/device data. Restrict read access and define retention.

### `notifications`

- `id` (UUID primary key)
- `user_id` (FK to `users`)
- `type`, short safe message, optional related transaction FK
- `created_at`, `read_at`

Notifications are owner-scoped. Do not include secrets or real financial data.

## Relationships and constraints

- `users` 1:1 `user_profiles`; `users` 1:1 `demo_accounts` for the initial product.
- `users` 1:N `server_sessions`, `password_reset_requests`, `security_audit_events`, and `notifications`.
- `demo_accounts` 1:N `transactions` as sender or recipient and 1:N `ledger_entries`.
- `transactions` 1:N `ledger_entries`; posted transfer constraints require exactly one debit and one credit.
- `users` 1:N `idempotency_records`; each completed transfer record references at most one transaction.
- Protect ownership with server-side query scoping and authorization on every object endpoint; opaque UUIDs are not authorization.

## Transaction integrity rules

1. Determine the sender account from the authenticated user.
2. Validate amount, maximum, account states, and recipient before mutating balances.
3. Claim the user/operation/idempotency key under a uniqueness constraint.
4. Lock both PostgreSQL account rows in a consistent order, or use a conditional atomic debit with a sufficient-balance predicate.
5. Within one transaction, update account balance projections, insert the transfer and its two ledger entries, and complete the idempotency record.
6. Verify debit/credit equality and commit. On any exception, roll back every monetary write and surface a safe error.
7. Generate a receipt only after confirmed commit.

## Retention and deletion

- Provide a documented demo-account deletion path that deletes or anonymizes profile, sessions, notifications, and user-associated demo records according to the chosen retention policy.
- Revoke sessions on deletion and account disablement.
- Define explicit retention windows for audit events, idempotency records, and failed recovery requests before deployment.
- Ledger retention and deletion policy must remain internally consistent: if preserving ledger integrity requires anonymization instead of deletion, disclose that clearly in the privacy notice. Do not silently retain identifiable data.
