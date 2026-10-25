
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

## Important limitations

- Transfers are blocked by the API with HTTP 503 until an approved payment provider is integrated. The app does not show seeded balances, synthetic recipients, transaction records, or receipts.
- Scan & Pay, receive-money, bank linking, bill payments, recharges, due-date reminders, rewards, refunds, and disputes are unavailable until their respective providers and operational workflows are integrated.
- Authentication uses an opaque HttpOnly session cookie and a session-bound CSRF token. Registration does not issue an opening balance.
- The backend keeps account and security controls, but financial activity endpoints intentionally return no provider transactions. Do not use the application to make or receive payments.
- Production configuration requires secure session cookies and PostgreSQL `sslmode=verify-full`. Configure HTTPS at the reverse proxy/load balancer. PostgreSQL-specific migration/trigger behavior and concurrent transfer handling have not been exercised here; SQLite does not provide equivalent row-lock concurrency guarantees.
- Account recovery returns an explicit unavailable error until a verified contact method and recovery provider are configured. Mobile verification, OTP delivery, and hardware-bound device authentication are not implemented; current sessions can be reviewed and revoked but do not establish cryptographic device binding.
- Security events are persisted in the audit table and notable failures are written to application security logs with request IDs. External monitoring/alert delivery and incident response are not configured. Production database least-privilege access, at-rest encryption, and encrypted backups must be configured and verified with the hosting provider; local SQLite is not encrypted by the application.
- This project is not a production banking application and has not received an independent security assessment.
=======
💳✨ **SecurePay — Smart, Simple & Secure Digital Payments** 🔐🚀

Welcome to **SecurePay**, a modern digital banking and payment application prototype inspired by today's popular payment platforms. Designed with a focus on simplicity, convenience, and user privacy, SecurePay demonstrates how digital payments can be organized through a clean, intuitive, and user-friendly interface.

🌟 **Key Features**

💸 **Simulated Money Transfers:** Experience a demo payment workflow with sender and recipient validation, transaction confirmation, and payment status tracking.

📱 **QR Payment Interface:** Explore a QR-based payment experience designed to make digital transactions quick and convenient.

📊 **Transaction History:** View previous demo transactions, payment statuses, transaction details, and reference numbers in one place.

👤 **User Account Management:** Explore registration, login, profile management, and account settings through a structured interface.

🔔 **Notifications:** View transaction updates and security-related notifications within the application.

🛡️ **Security-Focused Design:** Emphasizes secure password hashing, authentication, authorization, session management, input validation, and privacy-conscious handling of user data.

🔒 **Privacy by Design:** Encourages data minimization, restricted access to user information, secure configuration management, and responsible data handling.

🧪 **Demo Environment:** Uses simulated balances and transactions to demonstrate application workflows without transferring real money or connecting to real bank accounts.

🛠️ **Technology Stack**

- ⚛️ React and Vite for the frontend.
- 🐍 Python and FastAPI for backend APIs.
- 🗄️ SQLAlchemy and database integration for structured data management.
- 🔐 Secure authentication and server-side authorization.
- 🧪 Automated testing and security-focused validation.

🚀 **Project Objective**

The objective of SecurePay is to demonstrate how a modern digital payment application can combine a responsive user interface, backend services, database management, transaction workflows, and security-conscious development practices into one integrated project.

📚 **Learning and Development**

SecurePay is suitable for learning full-stack development, REST API integration, database design, authentication, payment workflow modeling, and application security. The project can be extended with additional features such as budgeting tools, spending analytics, recurring payment simulations, and authorized payment-provider integrations.

🔐 **Our Principle:** Your privacy matters. Security comes first. Every transaction deserves transparency.

💚 **Simple. Smart. Secure. Your Money, Your Control.**

⚠️ **Disclaimer:** SecurePay is a demonstration project. All balances and transactions are simulated. It is not a licensed bank, does not independently provide real UPI transfers, and must not be used to process real customer funds. Real payment functionality requires authorized payment partners, applicable regulatory compliance, and appropriate security assessments.

