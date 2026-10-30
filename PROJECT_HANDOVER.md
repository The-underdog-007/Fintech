# Seamless Payments — Project Handover

**Review date:** 30 October 2026  
**Project state:** Local prototype; deployment configuration prepared, but no production deployment has been created or verified.  
**Safety note:** This is a payment simulation. It does not connect to banks, NPCI, UPI, IMPS, NEFT, RTGS, or move real money.

## 1. Project overview

### Name, purpose, and objectives

**Seamless Payments** is a full-stack fintech prototype for the Indian payments context. It demonstrates a unified dashboard for fictional accounts at multiple banks, simulated transfers over UPI/IMPS/NEFT/RTGS, merchant-facing tools, and rule-based transaction risk checks.

Its objectives are to demonstrate:

1. A single interface for fictional accounts at multiple institutions.
2. A payment flow with balance validation, transaction PIN validation, idempotency support, fraud scoring, and an additional OTP challenge for high-risk payments.
3. Basic merchant, transaction-history, security-audit, and dispute-management experiences.

### Problem statement and proposed solution

Users often interact with separate bank interfaces and payment experiences. The prototype presents the concept of one interface that aggregates institution accounts and exposes familiar Indian payment rails. Its proposed solution is a React single-page application backed by a FastAPI REST API and a SQLite database. Bank connections, balances, OTP delivery, merchant payments, and payment rails are simulated locally.

## 2. Technology and architecture

| Layer | Implementation |
|---|---|
| Frontend | React, TypeScript, Vite, React Router, Recharts, Lucide icons, hand-authored CSS |
| Backend | Python, FastAPI, Uvicorn, Pydantic request models |
| Database | SQLite, initialized on API startup; seed rows are added when no user exists |
| Authentication | HS256 JWT via `python-jose`; password/PIN/OTP hashes via Passlib `pbkdf2_sha256` |
| Charts | Recharts AreaChart and BarChart |
| Styling | Custom CSS design system and responsive breakpoints; Tailwind is not included in this implementation |
| Frontend API URL | `VITE_API_URL`, defaulting to `http://localhost:8000/api` |
| CORS | `CORS_ORIGINS`, a comma-separated allowlist; defaults to `http://localhost:5173` |

The browser application is served by Vite during development and built to `frontend/dist`. `BrowserRouter` handles client-side paths. The FastAPI app exposes JSON under `/api`. The frontend stores the JWT and user object in `localStorage`, then sends the token as a Bearer credential. SQLite access is implemented directly with Python's `sqlite3`; connections are opened per API operation.

## 3. Database structure

The API creates these tables in `backend/seamless.db` (or the path set by `DATABASE_PATH`). Foreign keys are enabled on each SQLite connection.

| Table | Important columns | Relationships / purpose |
|---|---|---|
| `users` | `id`, `name`, `email` (unique), `password`, `pin`, `phone`, `role`, `created` | Parent identity for accounts, beneficiaries, transactions, disputes, merchants, audits, and OTP rows. Password and PIN are stored as password hashes. |
| `accounts` | `id`, `user_id`, `bank`, `label`, `number`, `ifsc`, `balance`, `color` | Belongs to a user; payment references an account as its source. `user_id` has a declared FK to `users`. |
| `beneficiaries` | `id`, `user_id`, `name`, `vpa`, `bank`, `verified` | User's saved payment destinations; used as one signal by fraud scoring. |
| `transactions` | `id`, `user_id`, `recipient`, `vpa`, `amount`, `rail`, `status`, `risk_score`, `risk_level`, `risk_reason`, `account_id`, `idempotency`, `reference`, `created` | Payment history; `user_id` and source `account_id` are stored. The `idempotency` column is unique. |
| `disputes` | `id`, `user_id`, `transaction_id`, `reason`, `status`, `created` | Dispute records associated with a user's transaction. |
| `merchants` | `id`, `user_id`, `name`, `category`, `vpa`, `created` | Merchant profiles belonging to a user. |
| `audit` | `id`, `user_id`, `action`, `detail`, `created` | Append-only style event records for selected operations such as OTP request, payment, account/beneficiary/merchant creation, and dispute creation. |
| `otp` | `id`, `user_id`, `code`, `expires`, `used` | Hashed simulated OTP challenge with expiry and one-use marker. |

There are no declared foreign-key constraints on every child table, and the model does not include separate banks, settlements, refunds, complaints, or payment-link/QR records. Amounts are SQLite `REAL` values, not a production-grade decimal-money model.

## 4. Implemented features

### Dashboard and account overview

- Lists linked account balances and a total balance.
- Shows recent transaction rows, monthly-spend total, payment count, and flagged count.
- Shows a six-month spending chart. Five historical chart values are fixed sample values; the latest uses the computed 30-day successful-payment total or a fallback sample.
- Shows payment methods as fixed illustrative UPI/debit-card content.

### Payments

- Form supports UPI, IMPS, NEFT, and RTGS selections.
- Requires recipient name/VPA, positive amount up to ₹500,000, a source account, and transaction PIN.
- Known beneficiaries can be selected through quick-send buttons or an input datalist.
- Backend validates rail, account ownership, available balance, PIN, and fraud score.
- A high-risk transfer requires the simulated OTP; after OTP validation the transaction is saved as `flagged` and is not deducted from the source balance.
- Low- and medium-risk transfers are saved as `success` and debited from the source account.
- The client makes a new idempotency UUID for each submission. The API can return an existing record for a repeated key, but the UI does not reuse a key when the user retries.
- Confirmation shows reference, rail, amount, risk result, and reason where relevant.

### Bank accounts and beneficiaries

- Seeded SBI, HDFC, and ICICI accounts have fictional balances and masked-style account labels.
- The link-account form accepts SBI, HDFC, ICICI, Axis, Kotak Mahindra, and Punjab National Bank; it creates a simulated account with a demo opening balance.
- Beneficiary list is seeded with three fictional people. The form adds name, VPA, and selected bank.
- No bank OAuth, account verification, statement sync, or real account-number validation exists.

### Merchant experience

- User can add a merchant profile with name, category, and VPA.
- Demo profiles are seeded for Blue Tokai Coffee, The Whole Truth, and Urban Company.
- Sales, transaction, customer, and settlement figures and the weekly chart are hard-coded sample data, not derived from transactions.
- “Payment QR” displays an alert with the merchant VPA; it does not render a QR code.
- “Payment link” copies a constructed `pay.seamless.in` URL and shows an alert; the URL is not backed by a payment-link endpoint.
- Settlement tool shows a simulation alert; no settlement records or payout processing exist.

### Fraud and security

Fraud scoring starts at 5 and adds:

| Rule | Points |
|---|---:|
| Beneficiary is not saved | +28 |
| Amount is at least ₹50,000 | +36 |
| Or amount is at least ₹20,000 | +19 |
| At least four transactions are found in the preceding hour | +24 |
| Amount is at least ₹10,000 and beneficiary is unfamiliar | +16 |

The score is capped at 100. Risk labels are `low` for 0–34, `medium` for 35–69, and `high` for 70–100. Reason strings explain triggered rules. The frequency rule counts stored user transactions regardless of their status. A high-risk transfer asks for OTP and is then flagged for review; there is no review-queue action to release, reject, refund, or close it.

Security mechanisms actually present:

- Password and transaction PIN hashes using PBKDF2-SHA256 through Passlib.
- 12-hour HS256 JWTs.
- Bearer-token authorization on user data endpoints.
- User-scoped account, beneficiary, transaction, and dispute queries in the principal read/write flows.
- Simulated OTP hashed in the database, marked used on successful high-risk verification, and set to expire after five minutes.
- Audit rows for selected security and financial events.

The `/api/auth/otp` endpoint returns the fixed demo OTP `123456` in its response. New registrations receive the fixed transaction PIN `1234`. This is demonstration behavior, not secure OTP delivery or a production enrollment flow.

### Transactions and disputes

- Transaction history supports text search by recipient/VPA/reference, status filtering, and rail filtering.
- CSV export is generated in the browser from the currently loaded filtered results.
- Statuses in the database/UI include successful, pending, failed, and flagged. The payment processor itself creates success or flagged records; a pending transaction is only present in seeded demo data, and no current flow creates failed transaction records.
- Users can file a dispute against one of their transactions and see created cases as under review.
- There is no refund-request endpoint or refund execution, nor a complaint tracking lifecycle beyond the basic dispute record.

### Admin view

- Displays global counts for users, transactions, successful volume, flagged payments, and disputes.
- Shows static illustrative subsystem and rail health rows.
- The fraud review queue is a static empty state.
- There is no role-based admin authorization: any authenticated user can call the admin endpoint and load the admin page.

## 5. Screens and routes

The development base URL is `http://localhost:5173`. The frontend is published at `https://seamless-payments.vercel.app`. Routes other than `/`, `/login`, and `/register` require a stored session; without one, the app redirects to `/login`. The FastAPI backend is not deployed, so API-backed sign-in is unavailable on the public site; use the interactive demo mode there until the backend is deployed.

**Interactive demo mode:** The sign-in page has an **Enter interactive demo** button. It bypasses API authentication and uses seeded fictional data plus localStorage mutations in the browser. It supports the main dashboard, account, beneficiary, transaction, payment, security, merchant, and dispute views without the backend. This is a frontend-only simulation; demo records stay in that browser and do not sync to SQLite or another device. Normal email/password sign-in still calls the configured API.

| Route | Screen and components | Useful screenshot interactions / data |
|---|---|---|
| `/` | Landing page; brand/navigation, hero account card, transfer/security badges, three feature cards, footer | Show “Get started”, “Explore demo”, and the feature section. “How it works” links to `#how`, but no element with that id is implemented. |
| `/login` | Sign-in form, demo account hint, explicit interactive-demo button, security copy, link to registration | On a local backend, sign in with `demo@seamless.in` / `Seamless@123`. On the public frontend, choose **Enter interactive demo**; this uses browser-local data and needs no API. |
| `/register` | Name, email, optional phone, password form | Register a new local demo user. New users receive PIN `1234`; they have no seeded bank accounts or beneficiaries and must add a simulated bank before sending a payment. |
| `/dashboard` | Balance/stat cards, spending area chart, account list, recent activity, payment methods, security banner | Demo user shows SBI/HDFC/ICICI, sample transactions, and balances. Use Send money to open payment flow. |
| `/payments` | Rail picker, recipient/VPA input, amount, source account, PIN, quick-send, payment result modal | Try a known beneficiary for a low-risk success. For high-risk/OTP: use a new VPA and amount high enough to cross 70 (e.g. ₹50,000 or more), enter PIN `1234`, choose Send verification code, then submit with OTP `123456`. This creates a flagged transaction and does not debit balance. |
| `/accounts` | Total balance, linked-account cards, supported-bank list, link-account modal | Link Axis/Kotak/PNB or another accepted simulated bank. The added account gets a fictional ₹25,000 balance by default. |
| `/beneficiaries` | Beneficiary cards and add-beneficiary form | Add a new VPA; then use it in Payments to demonstrate the unfamiliar-beneficiary rule. |
| `/transactions` | Summary cards, searchable/filterable table, CSV export | Filter status/rail, search a seeded recipient, or export the displayed result set. Seed data includes an NEFT pending row. |
| `/merchant` | Merchant workspace, sample KPI cards, sales bar chart, payment tools, merchant list, registration modal | Register a merchant. Payment QR, link, and settlement controls are demo interactions (alerts/copy), not server-backed payment/settlement processing. |
| `/security` | Security score illustration, static security assertions, audit event list, risk legend, elevated-risk transaction table | After sending a payment or requesting OTP, navigate here to show audit entries and any medium/high risk transactions. |
| `/disputes` | Dispute help banner, case list, raise-dispute form | Open a dispute against a seeded or newly-created transaction; it appears as under review. No refund flow is available. |
| `/admin` | Platform counts, demo warning, static service/rail health, static empty review queue | Open as any signed-in demo user; it is not restricted to an admin role. |

Shared app shell: sidebar route navigation, workspace label, profile/logout, breadcrumb, search field (visual only), notification icon (visual only), and operational/simulation footer. On narrow screens, the sidebar becomes a slide-in menu.

## 6. API inventory

API base URL locally: `http://localhost:8000`. Interactive docs locally: `http://localhost:8000/docs`.

| Method and path | Auth | Purpose |
|---|---|---|
| `GET /api/health` | No | Health check; returns simulation mode. |
| `POST /api/auth/register` | No | Creates a user, hashes password, assigns demo PIN `1234`, returns JWT and profile. |
| `POST /api/auth/login` | No | Verifies email/password and returns JWT/profile. |
| `POST /api/auth/otp` | Bearer | Creates hashed, five-minute simulated OTP; returns demo code `123456`. |
| `GET /api/dashboard` | Bearer | Returns accounts, latest eight transactions, balance/spend/count metrics and chart series. |
| `GET /api/accounts` | Bearer | Lists the signed-in user's accounts. |
| `POST /api/accounts` | Bearer | Adds an allowed simulated bank account. |
| `GET /api/beneficiaries` | Bearer | Lists the user's beneficiaries. |
| `POST /api/beneficiaries` | Bearer | Adds a beneficiary. |
| `POST /api/payments` | Bearer | Validates PIN/account/balance, scores risk, enforces high-risk OTP, records transaction/audit, and debits only successful payments. Request includes `idempotency_key`. |
| `GET /api/transactions` | Bearer | Lists own transactions; query parameters `status`, `rail`, and `q` filter results. |
| `POST /api/disputes` | Bearer | Creates a dispute only for a transaction owned by the user. |
| `GET /api/disputes` | Bearer | Lists the user's dispute cases. |
| `GET /api/merchants` | Bearer | Lists the user's merchant profiles. |
| `POST /api/merchants` | Bearer | Registers a merchant profile. |
| `GET /api/security` | Bearer | Returns latest audit events and non-low-risk transactions. |
| `GET /api/admin` | Bearer | Returns global prototype counts and volume; no role check. |

There are no API endpoints for account unlinking, real bank verification, refunds, QR generation, payment links, settlements, admin review actions, or user settings.

## 7. Demo data and credentials

- User: `demo@seamless.in`
- Password: `Seamless@123`
- Transaction PIN: `1234`
- Simulated OTP: `123456`
- Seed account balances: SBI ₹82,450; HDFC ₹142,800; ICICI ₹36,720 (total ₹261,970 at initial seed).
- Seed beneficiaries: Priya Sharma (`priya@okaxis`), Rohan Kapoor (`rohan@okhdfcbank`), Maya Iyer (`maya@oksbi`).
- Seed merchants: Blue Tokai Coffee, The Whole Truth, Urban Company.
- Seed transactions: six examples, including one pending NEFT record.

The database persists on the local filesystem when run locally. Deleting `backend/seamless.db` and restarting causes a fresh demo seed. Demo credentials and deterministic OTP must not be used as real account security.

## 8. Deployment assessment and prepared configuration

### Recommended deployment shape

- **Frontend:** Vercel static Vite build, with Vercel project root set to `frontend`. `frontend/vercel.json` configures the build output and SPA fallback rewrite so BrowserRouter deep links load.
- **API and persistent data:** A separate FastAPI service. `render.yaml` is prepared for a Render web service rooted at `backend`, with a disk mounted at `/var/data`, SQLite at `/var/data/seamless.db`, a generated `JWT_SECRET`, `/api/health` health check, and a `CORS_ORIGINS` secret/configuration value. Render documents persistent disks as available on paid services; a disk is required to retain SQLite across restarts/deploys. Alternatively migrate the API to a managed PostgreSQL service before choosing a serverless host.
- **Frontend API connectivity:** `VITE_API_URL` can point to the public API base ending in `/api`. Without it, the development default is localhost.
- **CORS:** `CORS_ORIGINS` on the API must include the exact public Vercel origin (for example `https://your-project.vercel.app`) and, if desired, `http://localhost:5173`.

Vercel's Vite guidance calls for an SPA rewrite to support deep links; the supplied `frontend/vercel.json` provides that rewrite. Render's documentation states that service filesystems are ephemeral by default and persistent disks require a paid service; the supplied blueprint attaches the disk. [Vercel Vite deployment docs](https://vercel.com/docs/frameworks/frontend/vite), [Vercel configuration docs](https://vercel.com/docs/project-configuration/vercel-json), [Render persistent disk docs](https://render.com/docs/disks).

### Deployment status and blockers

**Frontend deployed; backend not deployed.** The Vercel production URL is `https://seamless-payments.vercel.app`, and root plus all SPA routes returned HTTP 200 during deployment verification. The Vercel CLI could not connect the GitHub repository for automatic deploy-on-push integration, but direct production deploys succeeded. The FastAPI API and persistent database still need a separate authenticated backend host; the Vercel static deployment alone cannot preserve SQLite or enable API-backed flows.

Files prepared for deployment:

- `frontend/vercel.json` — build output and SPA route fallback.
- `frontend/.env.example` — frontend API URL setting.
- `render.yaml` — separate FastAPI service and persistent disk blueprint; CORS is set to the deployed Vercel origin plus local development.
- API CORS now reads `CORS_ORIGINS` (local default remains `http://localhost:5173`).

Required post-deployment settings:

| Location | Variable | Value |
|---|---|---|
| Vercel frontend project | `VITE_API_URL` | `https://<actual-backend-host>/api` |
| Render API service | `JWT_SECRET` | Generated by the blueprint; use a unique secret in production. |
| Render API service | `DATABASE_PATH` | `/var/data/seamless.db` (set by blueprint, disk-mounted path). |
| Render API service | `CORS_ORIGINS` | The exact Vercel production origin, optionally comma-separated with local dev origin. |

After backend account/source access is available, deploy the API first, set its resulting URL into Vercel's `VITE_API_URL`, add the Vercel URL to API `CORS_ORIGINS`, redeploy both, then verify health, API login, payment, fraud challenge, merchant registration, and dispute persistence against the public services. Public interactive demo mode works without that backend and stores mutations only in browser localStorage.

## 9. Known limitations and incomplete areas

1. Payment rails, bank connectivity, balances, OTP, merchant payments, and settlements are simulations only. The added browser-local demo mode is separate from the FastAPI-backed local demo and does not persist to the server database.
2. The frontend supports `VITE_API_URL`, but production does not yet have a backend URL configured. Normal API sign-in and server-backed actions remain unavailable publicly; the public interactive demo runs entirely in the browser.
3. SQLite is suitable for the local/demo single-process prototype. Production persistence depends on the configured persistent disk; this is not a horizontally-scalable database design.
4. The app defaults to a known development JWT secret when `JWT_SECRET` is unset. Production must use a generated secret.
5. The fixed OTP is returned by the API, registration sets the same PIN for every new user, and registration/login do not require OTP.
6. Admin routes are available to any authenticated user; `role` is not used for authorization.
7. Merchant analytics, QR, payment links, settlement figures, and system-health rows are static or alert-based UI, not real integrations.
8. No refund workflow, refund API, complaint lifecycle, flagged-payment review action, settlement ledger, or payment-link/QR persistence is implemented.
9. Payment submission UI creates a new idempotency key per submit, so users repeating a form submission do not reuse the prior key. The API's unique key also applies globally in SQLite, though lookup is user-scoped.
10. Several UI elements are presentational only (global search, notification icon, account overflow actions, some dashboard/payment-method values). They should not be represented as working backend features.
11. No formal automated test suite or production integration test suite is present. Frontend production build and backend import/initialization were checked locally; no public production workflows have been tested.
