# SecurePay frontend

Responsive React/Vite frontend for the SecurePay account dashboard. No bank or payment provider is connected, so payment features are disabled.

## Run locally

Requirements: Node.js 20.19+ (or 22.12+) and npm. Start the backend first using the instructions in the root `README.md`.

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). Vite proxies `/api` requests to `http://127.0.0.1:8000`.

## Available flows

- Authenticated dashboard with provider-connection status and account security.
- Account registration followed by a separate sign-in, sign-out, and generic recovery request (delivery is not configured).
- Send, receive, bank-linking, and scan flows clearly report that a provider is not connected and do not initiate transactions.
- Transaction history displays no records until provider-confirmed activity is available.
- Backend-persisted profile editing, notifications/read controls, security preferences, and active-session revocation.
- Password changes that revoke other sessions.

The frontend keeps only the CSRF token in JavaScript memory; authentication uses the backend's HttpOnly session cookie. The UI uses no analytics or third-party tracking.

## Production build

```powershell
npm run build
npm run preview
```

The application does not process payments. Provider onboarding, authorization, regulatory review, and security validation are required before real-money features can be implemented.
