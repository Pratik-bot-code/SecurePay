
# SecurePay

SecurePay is a responsive account dashboard built with React/Vite and FastAPI. It supports account sign-in, profile management, notifications, and session/security controls. Payment features remain unavailable because no bank, UPI, card, biller, or payment provider is connected. The application does not send or receive money.

## Local development

Requirements: Python 3.11+ and Node.js 20.19+ (or 22.12+). SQLite is the default local database; PostgreSQL is the intended production database.

### Backend

In a PowerShell terminal:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`; local API documentation is at `/api/docs`. Database schema creation is migration-only. Apply `alembic upgrade head` before starting the API. The backend does not seed payment recipients or balances.

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` or the URL shown by Vite. Vite proxies `/api` to the local FastAPI service. Create a SecurePay account using a 3–30 character Profile ID made of letters, numbers, periods, underscores, or hyphens (not an email address), then sign in with the new credentials. The account starts without a bank balance or payment history.

### Local startup troubleshooting

- If Uvicorn reports a socket bind/access error on port 8000, the backend is likely already running. Use the existing API at `http://127.0.0.1:8000/api/health` instead of starting a second copy, or stop the existing server with `Ctrl+C` in its terminal before restarting.
- To run another backend on port 8001, start it with `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001`. In the frontend terminal, set `$env:SECUREPAY_API_TARGET = "http://127.0.0.1:8001"` before `npm run dev`. Restart Vite after changing this setting.
- Account creation displays field-specific messages for invalid Profile IDs and password length. If the API cannot be reached, the sign-in page points to the backend health URL.

### Tests and production build

From the backend directory, with the database configured and migrated:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m alembic check
```

From the frontend directory:

```powershell
npm run build
```

## Important limitations & security notes

- **Demonstration & Sandbox Scope**: SecurePay is a security-conscious payments application prototype. All balances and transaction workflows operate in simulated sandbox mode. It does not independently operate as a licensed bank, does not collect or store UPI PINs or card CVVs, and must not be used to process real customer funds without an authorized payment gateway partnership and compliance review.
- **Provider Gate**: Unbacked financial transfers are blocked with HTTP 503 until an approved payment partner (such as Razorpay/Cashfree Sandbox) is integrated.
- **Authentication & Sessions**: Authentication relies on Argon2id password hashing, opaque HttpOnly session cookies, and session-bound HMAC-SHA256 CSRF protection.
- **Production Requirements**: Production deployments require secure cookies, HTTPS termination at reverse proxy/load balancer, and PostgreSQL configured with `sslmode=verify-full`.
- **Audit Logging**: Security-relevant events (failed logins, authorization denials, rate limit hits) emit structured audit records with correlated Request IDs.
- **Privacy by Design**: Strict data minimization is enforced. Sensitive payment credentials (PIN, CVV, OTP) are never requested, transmitted, or stored.

