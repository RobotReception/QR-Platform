# QR-Platform (Qentry)

> Multi-tenant digital invitation & event check-in platform — منصة الدعوات الرقمية وتسجيل الدخول للفعاليات

QR-Platform is a SaaS application for creating event invitations from templates,
generating QR/barcode passes in bulk, and validating guests at the gate in
real time. It supports multiple tenants, role-based access control, billing
(Stripe & PayPal), and Arabic/RTL-aware rendering.

> **Note:** The repository also contains an Arabic status document at
> [`README_AR.md`](./README_AR.md) and detailed guides under the various
> `*.md` files (see [`DOCUMENTATION_INDEX.md`](./DOCUMENTATION_INDEX.md)).

---

## Features

- **Multi-tenancy** — tenant isolation via the `X-Tenant-ID` header / subdomain / custom domain.
- **Template-based invitations** — design templates with relative (0.0–1.0) element coordinates, RTL mirroring, and Arabic text shaping.
- **Bulk generation** — offload PDF/ZIP batch generation to Celery workers (with a BackgroundTask fallback for dev).
- **Check-in** — high-throughput gate scanning endpoint with HMAC-signed invitation tokens.
- **Billing** — Stripe and PayPal subscriptions, plans, add-ons and usage quotas.
- **Auth** — Supabase Auth (JWT), RBAC, and audit logging.

## Tech Stack

| Layer    | Technology |
|----------|------------|
| Backend  | FastAPI, SQLAlchemy (asyncpg), Pydantic v2 |
| Workers  | Celery + Redis |
| Database | PostgreSQL (via Supabase or self-hosted) |
| Auth/Storage | Supabase |
| Frontend | React 18, TypeScript, Vite, TanStack Query, Zustand, Tailwind CSS |
| Payments | Stripe, PayPal |
| Rendering | Pillow, ReportLab, PyMuPDF, qrcode, python-barcode |

## Project Structure

```
app/                  FastAPI backend
  ├─ routes/          API routers (auth, events, templates, checkin, billing, ...)
  ├─ services/        Business logic (render, batch pipeline, permissions, ...)
  ├─ models/          SQLAlchemy models
  ├─ main.py          App entrypoint & middleware wiring
  ├─ auth.py          JWT verification
  └─ middleware.py    Tenant resolution, security headers, rate limiting
frontend/             React + Vite SPA (Qentry)
  └─ src/features/     Feature-based modules (auth, dashboard, events, ...)
landing/              Marketing landing page
supabase/             SQL schema & manual migrations
scripts/              Operational scripts
tests/                Automated tests (pytest)
docker-compose.yml    Local Postgres + Redis
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (for local Postgres + Redis)

### 1. Backend

```bash
# Clone & enter
git clone https://github.com/RobotReception/QR-Platform.git
cd QR-Platform

# Configure environment
cp .env.example .env
# → fill in Supabase, database, Stripe/PayPal, SMTP and INVITE_HMAC_SECRET values

# Start Postgres + Redis
docker compose up -d

# Install Python deps
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the API
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### 2. Celery worker (optional, for bulk generation)

```bash
celery -A app.worker.celery_app worker --loglevel=info
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on http://localhost:5173 and proxies `/api/v1` to the backend.

## Environment Variables

See [`.env.example`](./.env.example) for the full list. Key groups:

- **Supabase:** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
- **Database:** `DATABASE_URL` (`postgresql+asyncpg://...`)
- **Billing:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`
- **Security:** `INVITE_HMAC_SECRET` (required in production — generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
- **Worker/Storage:** `REDIS_URL`, `USE_WORKER`, `STORAGE_BUCKET`

> **Never commit secrets.** `.env` and token files (e.g. `auth-data.json`) are gitignored.

## Testing

```bash
# Backend
pip install -r requirements-dev.txt
pytest

# Frontend
cd frontend
npm run lint
npm run build
```

## API Documentation

A comprehensive endpoint reference lives in [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md).
All authenticated requests require both an `Authorization: Bearer <token>` header
and an `X-Tenant-ID` header.

## License

See [`LICENSE`](./LICENSE).
