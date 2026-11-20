# Frontend Operations Client

The frontend is a React/Vite client for the simulated banking fraud backend. It
does not implement ledger arithmetic, fraud rules, ML inference, or persistence.

## Features

- JWT login through `POST /api/v1/auth/login`.
- Role-aware navigation for customers, investigators, and administrators.
- Account and customer views.
- Transfer submission with C++ risk evaluation results.
- Transaction history and risk/status display.
- Fraud-alert review, status updates, and investigation opening.
- Investigation notes, review actions, and close outcomes.

## Local development

```powershell
npm ci
$env:VITE_API_BASE_URL = "http://localhost:8000/api/v1"
npm run dev
```

The default API base URL is `http://localhost:8000/api/v1`. The backend must
have CORS configured for the Vite origin, which is the default development
configuration.

## Build

```powershell
npm run build
```

The frontend workflow runs this build on frontend source or workflow changes.
