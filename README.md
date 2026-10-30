# Seamless Payments

A local fintech prototype for simulated interoperable Indian payments. It pairs a React + TypeScript dashboard with a FastAPI API and a SQLite database. No real bank or payment rail is contacted.

## Run locally

Requirements: Python 3.10+ and Node.js 18+.

1. Start the API:
   ```bash
   cd backend
   python -m venv .venv
   # Windows: .venv\\Scripts\\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
2. In a second terminal, start the client:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Open http://localhost:5173. Demo login: `demo@seamless.in` / `Seamless@123` (OTP: `123456`, transaction PIN: `1234`).

API docs are at http://localhost:8000/docs. Set `JWT_SECRET` before exposing the API beyond local development. OTP delivery is simulated and OTP/PIN values are seeded for this demo only.

## Features

- JWT login and registration, password hashing, simulated OTP, transaction PIN challenge.
- Linked bank accounts, beneficiaries, simulated UPI/IMPS/NEFT/RTGS transfers, idempotency keys, audit trail.
- Rule-based risk assessment with score, category, reason codes, and additional verification for high-risk payments.
- Transactions, disputes, merchant registration, QR/payment-link simulation, settlement and admin overview.

All balances and transactions are fictional demo data. This is not a banking product and does not connect to UPI, IMPS, NEFT, RTGS, or any financial institution.
