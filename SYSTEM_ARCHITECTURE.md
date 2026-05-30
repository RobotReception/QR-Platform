# Digital Invitations Platform — Production Spec v4.1 Final

> **Stack**: FastAPI + PostgreSQL + Supabase Auth/Storage + Stripe + Celery/Redis
> **Current Snapshot**: 120 Endpoints · 34 Tables · 75+ RLS Policies · 18 DB Functions

---

## 1. System Overview

Multi-tenant SaaS platform for digital event invitations:
- **Event Management**: Categories, types, venues, quotas, gates
- **Invitation Lifecycle**: created → sent → viewed → accepted → checked_in (8 states)
- **Template Designer**: Relative coordinates (0→1) + Arabic RTL
- **QR/Barcode**: HMAC-signed (dedicated key + rotation), cloud-stored
- **Batch Pipeline**: Celery worker → barcodes → images → PDF → ZIP (tempfile streaming)
- **Atomic Check-in**: SELECT FOR UPDATE locking, gate/class validation
- **Multi-tenancy**: Row-Level Security on every table
- **Data Integrity**: SQL CHECK constraints on coords, quotas, fonts, batch immutability

### Architecture Diagram

```
CLIENT (Web/Mobile)
    │ HTTPS + JWT + X-Tenant-ID
    ▼
┌─ MIDDLEWARE ──────────────────────────────────────┐
│ CORS → RateLimit(120/min, 30/min public)          │
│ → SecurityHeaders → TenantResolution              │
└───────────────────────┬──────────────────────────-┘
                        ▼
┌─ FastAPI API (120 endpoints) ────────────────────-┐
│ 14 Route Files → 12 Services → 7 Model Files     │
└──────┬────────────────┬──────────────┬───────────-┘
       │                │              │
       ▼                ▼              ▼
  PostgreSQL      Supabase Storage    Stripe
  (34 tables)     (bucket:invitations) (billing)
  + RLS (75+)     (private + signed)
  + Triggers (6)
       │
       ▼
┌─ Celery Worker (Redis broker) ───────────────────┐
│ batch.run_pipeline task                           │
│ acks_late + reject_on_worker_lost + max_retries=2 │
│ Fallback: BackgroundTask (dev only)               │
└──────────────────────────────────────────────────-┘
```

### Terminology

Throughout this spec, **Tenant** = organization/company. Used consistently everywhere.

---

## 2. Project Structure

```
app/
├── main.py              # FastAPI app + router registration
├── config.py            # Settings + HMAC keys + Redis + expiry config
├── database.py          # SQLAlchemy async + Supabase client
├── auth.py              # JWT verification
├── middleware.py         # Tenant + RateLimit + Security
├── worker.py            # Celery worker (Redis broker, batch tasks)
├── tenant_context.py    # Context vars for current tenant
├── models/              # Pydantic schemas (7 files)
│   ├── event.py         #   Event, Category, Type, Gate, Stats
│   ├── invitation.py    #   Invitation, Checkin, RSVP, Delivery
│   ├── template.py      #   Template, Element, Asset
│   ├── guest.py         #   Guest + custom_fields
│   ├── batch.py         #   Batch, BatchItem, LayoutConfig (+ snapshot policy)
│   └── team.py          #   Team + Membership
├── routes/ (14 files)   # API endpoints
│   ├── events.py        #   events + categories + types + gates + stats
│   ├── digital_invitations.py  # create, quick, bulk, send, revoke, RSVP
│   ├── guests.py        #   CRUD + bulk import
│   ├── templates.py     #   CRUD + elements + assets + font governance
│   ├── checkin.py       #   scan, manual, history, live stats
│   ├── batches.py       #   create, start(→Celery), cancel, retry, download
│   └── auth, tenants, profiles, teams, subscriptions, roles, audit...
└── services/ (12 files) # Business logic
    ├── barcode_service.py     # QR gen + HMAC signing + key rotation
    ├── render_service.py      # Pillow composition + Arabic RTL + auto-fit
    ├── pdf_service.py         # ReportLab grid + per-page cards
    ├── batch_pipeline.py      # 5-phase orchestrator (tempfile streaming)
    ├── storage_service.py     # Supabase Storage (signed URLs, configurable expiry)
    └── permission_service.py, audit_service.py, provisioning_service.py...

supabase/
├── schema_final.sql                       # V1: SaaS core (17 tables)
├── migration_v3_invitations_platform.sql  # V3: Invitations (13 tables)
├── migration_v4_generation_batches.sql    # V4: Batches (2 tables)
├── migration_v5_production_hardening.sql  # V5: Atomic checkin + state machine
├── migration_v6_constraints_and_governance.sql  # V6: CHECK constraints + immutability
└── fix_and_seed.sql                       # Patches
```

---

## 3. Database Schema (34 Tables)

### 3.1 SaaS Core (V1) — 17 tables

| Table | Purpose |
|-------|---------|
| `profiles` | User accounts (synced from auth.users) |
| `tenants` | Organizations (slug, status, plan) |
| `tenant_domains` | Custom domains per tenant |
| `memberships` | User ↔ Tenant (role: owner/admin/member/viewer) |
| `roles` | RBAC roles per tenant (system + custom) |
| `permissions` | 62 permission keys |
| `role_permissions` | Role ↔ Permission mapping |
| `membership_roles` | User ↔ Role assignment |
| `plans` | Free / Pro / Enterprise |
| `plan_limits` | Entitlements per plan (quotas) |
| `subscriptions` | Stripe subscriptions |
| `subscription_events` | Billing audit trail |
| `usage_counters` | Monthly usage tracking |
| `invites` | Team member invitations |
| `tenant_settings` | Key-value config |
| `feature_flags` | Feature toggles |
| `audit_logs` | Full audit trail |

### 3.2 Digital Invitations (V3) — 13 tables

| Table | Purpose | Key Design |
|-------|---------|------------|
| `teams` | Internal teams | tenant-scoped |
| `team_memberships` | Team ↔ User | role: team_lead/member |
| `event_categories` | Classification | system + tenant-specific |
| `event_types` | Subtypes | linked to category |
| `events` | Events | vip_quota, normal_quota, allow_reentry |
| `event_gates` | Entry gates | allowed_classes[] (VIP/normal filter) |
| `invite_templates` | Designs | quick/designed, width_px×height_px |
| `template_elements` | Design elements | **relative coords (0→1)**, data_key, font_asset_id |
| `template_assets` | Files | background, font, overlay, logo |
| `guests` | Guest directory | custom_fields (JSONB) for dynamic data |
| `invitations` | Invitations | token(32 hex), status(8 states), barcode URLs |
| `invitation_deliveries` | Send log | channel: sms/email/whatsapp/link/print |
| `checkins` | Scan log | result(7 types), ip_address, device_info |

### 3.3 Generation Pipeline (V4) — 2 tables

| Table | Purpose |
|-------|---------|
| `generation_batches` | Batch jobs (status, progress 0-100, result URLs, metrics) |
| `batch_items` | Per-invitation tracking (render_status, barcode_url, render_url) |

### 3.4 Production Hardening (V5)

| Change | Purpose |
|--------|---------|
| `validate_checkin` → SELECT FOR UPDATE | Atomic check-in (prevents race condition) |
| `enforce_batch_transition` trigger | State machine (prevents invalid status jumps) |
| `generation_batches` + metrics columns | duration_ms, pdf/zip sizes, error_summary |
| `template_elements` + font_asset_id | Dynamic font loading from uploaded assets |
| `idx_checkins_ip_recent` index | Fast IP lookup for rate limiting |

### 3.5 Enums

```sql
tenant_status:     active, trial, suspended, cancelled, deleted
membership_role:   owner, admin, member, viewer
ticket_class:      vip, normal
invitation_status: created, sent, viewed, accepted, declined, checked_in, revoked, expired
delivery_channel:  sms, email, whatsapp, link, print
template_type:     quick, designed
element_type:      guest_name, event_title, event_date, event_time, event_location,
                   qr_code, barcode, seat_number, gate, hall, table_number, custom_text, image
rsvp_status:       pending, accepted, declined, maybe
checkin_result:    success, already_checked_in, revoked, expired, invalid, wrong_event, wrong_gate
batch_status:      draft, queued, generating_barcodes, rendering_images,
                   generating_pdf, generating_zip, ready, failed, cancelled
```

### 3.6 Key Indexes

```
invitations: tenant_id, event_id, token(UNIQUE), status, ticket_class,
             guest_id, (event_id,ticket_class), (event_id,status)
checkins:    (ip_address, created_at DESC) WHERE result != 'success'
generation_batches: tenant_id, event_id, status, created_at DESC
```

---

## 4. Authentication & Authorization

### 4.1 Auth Flow

```
Client → POST /auth/login {email, password}
  → Supabase Auth → JWT token
  → Client stores JWT

Client → GET /api/v1/events
  Headers: Authorization: Bearer <JWT>, X-Tenant-ID: <uuid>
  → Middleware: validate JWT → resolve tenant → check status
  → Route: get_current_user → require_permission("events.view")
  → Query with tenant_id filter
```

### 4.2 RBAC Model

```
User ──(membership)──→ Tenant (role: owner/admin/member/viewer)
  │
  └──(membership_roles)──→ Role ──(role_permissions)──→ Permission

Owner/Admin: bypass all permission checks (automatic)
Others: checked via user_has_permission(tenant_id, user_id, key)
```

### 4.3 Default Roles (5)

| Role | Permissions |
|------|-------------|
| **Admin** | All 62 permissions |
| **Member** | events.*, invitations.*, guests.*, batches.create/view, templates.view |
| **Designer** | templates.*, files.*, view-only for events/invitations |
| **Check-in Staff** | checkin.scan, checkin.manual, checkin.view, events.view |
| **Viewer** | *.view only + batches.view |

### 4.4 Row-Level Security — Design Decision

> **Decision: Option B — RLS for tenant isolation only; all writes via API + RBAC.**

RLS enforces **tenant data isolation** for **non-service-role** access paths
(anon/authenticated roles). All write operations go through the FastAPI API layer,
which checks RBAC permissions via `require_permission()`. For API queries executed
via `service_role`, RLS is bypassed; isolation is guaranteed by middleware +
TenantQuery + tenant_id immutability trigger (see §4.5 Guardrails).

**RLS policies (applied to every table):**
- **SELECT**: `tenant_id IN (SELECT get_my_tenant_ids())`
- **INSERT/UPDATE/DELETE**: `is_admin_of(tenant_id)` ← service_role bypasses this

**Write path (all mutations):**
```
Client → FastAPI → require_permission(db, tenant_id, user_id, 'events.update')
                 → SQL via service_role connection (bypasses RLS write policies)
                 → tenant_id always set from authenticated context (never from client)
```

**Why Option B (not permission-aware RLS):**
1. All writes go through FastAPI (no direct client→DB writes)
2. `require_permission()` checks 62 permission keys per endpoint
3. Owner/Admin bypass all permission checks automatically
4. Simpler RLS policies (no need for 62+ write policies per table)
5. Supabase service_role key used by API has full DB access

**Security guarantee:** Even if RLS write policy is `is_admin_of()`, a Member
with `events.update` permission can update events because the API uses service_role.
RLS only prevents cross-tenant data access on SELECT.

### 4.5 Option B Guardrails (service_role Safety)

Since `service_role` bypasses RLS entirely, these guardrails prevent accidental
cross-tenant data access or mutation:

#### Guardrail 1: Every query MUST include tenant_id (Enforced by Code)

All tenant-scoped route handlers **MUST** use `TenantQuery` helper (`app/services/tenant_query.py`),
which **automatically injects** `WHERE tenant_id = :tenant_id` into every query.
Direct `text()` SQL in tenant-scoped routes is forbidden except in migrations/admin scripts.

```python
from app.services.tenant_query import TenantQuery

tq = TenantQuery(db, tenant_id)                          # tenant_id from middleware
rows  = await tq.select("events", columns="id, title")   # auto: WHERE tenant_id = :tid
row   = await tq.select_one("events", where="id = :id", params={"id": eid})
count = await tq.update("events", set_clause="title = :t", params={"t": "New", "id": eid}, where="id = :id")
new   = await tq.insert("events", columns=["title"], values={"title": "X"})  # auto-adds tenant_id
```

**Safety features:**
- `TenantQuery.__init__` raises `ValueError` if `tenant_id` is None/empty
- `insert()` auto-adds `tenant_id` to columns; raises if mismatched value provided
- No way to issue a query without tenant_id through this helper

**Exception:** Public token endpoints (`/view/{token}`, `/rsvp/{token}`) query by
token only — the token is unique across all tenants, and responses return only
guest-safe fields (no tenant_id, no internal IDs).

#### Guardrail 2: tenant_id is immutable (DB Trigger)

A database trigger `prevent_tenant_id_change()` is **automatically applied** to every
`public` table that has a `tenant_id` column (discovered via `information_schema.columns`).
Any `UPDATE` that attempts to change `tenant_id` raises an exception:

```sql
-- Trigger function (V6 migration)
IF OLD.tenant_id IS DISTINCT FROM NEW.tenant_id THEN
    RAISE EXCEPTION 'Cannot change tenant_id';
END IF;
```

This is the **last line of defense** — even if a code bug tries to move a row
to another tenant, the database itself will reject it.

#### Guardrail 3: Ignore client-supplied tenant_id

The `tenant_id` used in all queries comes exclusively from:
1. `X-Tenant-ID` header → validated by `TenantResolutionMiddleware`
2. Verified against user's `memberships` (user must be a member of that tenant)

**Never** from request body, path parameters, or query strings.
Even if a client sends `tenant_id` in a POST body, it is overwritten by the
middleware-resolved value via `get_tenant_id_from_header(request)`.

#### Summary: Defense in Depth

```
Layer 1: Middleware     → resolves tenant_id from header + validates membership
Layer 2: RBAC           → require_permission() checks 62 keys per endpoint
Layer 3: TenantQuery    → every SQL auto-includes WHERE tenant_id = :tid (MUST use)
Layer 4: DB Trigger     → prevents tenant_id mutation on all tenant-scoped tables
Layer 5: RLS (SELECT)   → protects non-service-role access paths only (see note)
```

> **⚠️ Layer 5 caveat:** The API uses `service_role` which **bypasses RLS entirely**
> (SELECT/INSERT/UPDATE/DELETE). Therefore, RLS does NOT protect against cross-tenant
> reads within the API itself. Tenant isolation for API queries is guaranteed by
> **Layers 1–4 only** (Middleware + RBAC + TenantQuery + DB Trigger).
>
> RLS remains valuable for:
> - Direct client DB access via `anon`/`authenticated` roles (e.g., Supabase Realtime)
> - Defense against future access paths that don't go through the API
> - Compliance audits that require DB-level isolation proof on SELECT

---

## 5. API Endpoints Reference (120 total)

### Auth (8 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/signup` | Register |
| POST | `/auth/login` | Login → JWT |
| POST | `/auth/refresh` | Refresh token |
| GET | `/auth/me` | Current user |
| POST | `/auth/password-reset/request` | Request reset |
| POST | `/auth/password-reset/confirm` | Confirm reset |
| PATCH | `/auth/change-password` | Change password |
| POST | `/auth/logout` | Logout |

### Events (12 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/events/categories` | List categories |
| POST | `/events/categories` | Create category |
| GET | `/events/types` | List types |
| POST | `/events` | **Create event** |
| GET | `/events` | List events |
| GET | `/events/{id}` | Get event |
| PATCH | `/events/{id}` | Update event |
| DELETE | `/events/{id}` | Delete event |
| POST | `/events/{id}/publish` | Publish event |
| GET | `/events/{id}/stats` | Event statistics |
| GET | `/events/{id}/gates` | List gates |
| POST | `/events/{id}/gates` | Create gate |

### Invitations (12 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/invitations` | List (filter: event, class, status) |
| GET | `/invitations/{id}` | Get one |
| POST | `/invitations` | **Create single** (+ inline barcode) |
| POST | `/invitations/quick` | **Quick create** (by count or names) |
| POST | `/invitations/bulk-from-guests` | **Bulk from guest book** |
| PATCH | `/invitations/{id}` | Update |
| POST | `/invitations/{id}/revoke` | Revoke |
| POST | `/invitations/bulk-revoke` | Bulk revoke |
| POST | `/invitations/send` | Send (SMS/email/WhatsApp) |
| GET | `/invitations/view/{token}` | **Public**: view invitation |
| POST | `/invitations/rsvp/{token}` | **Public**: RSVP |

### Check-in (4 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/checkin/scan` | **QR scan** (atomic) |
| POST | `/checkin/manual` | Manual check-in |
| GET | `/checkin/history` | Scan history |
| GET | `/checkin/live/{event_id}` | Live stats + recent |

### Templates (12+ endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| POST/GET/PATCH/DELETE | `/templates` | CRUD |
| POST | `/templates/{id}/elements` | Add element |
| PUT | `/templates/{id}/elements` | Replace all elements |
| PATCH | `/templates/elements/{id}` | Update element |
| DELETE | `/templates/elements/{id}` | Delete element |
| POST | `/templates/{id}/upload-background` | Upload background |
| POST | `/templates/{id}/upload-asset` | Upload asset |
| DELETE | `/templates/assets/{id}` | Delete asset |

### Guests (6 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| POST/GET/PATCH/DELETE | `/guests` | CRUD |
| POST | `/guests/import` | Bulk import (JSON list) |
| GET | `/guests/search` | Search by name/phone |

### Batches (10 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/batches` | Create batch |
| GET | `/batches` | List batches |
| GET | `/batches/{id}` | Get with progress |
| POST | `/batches/{id}/start` | **Start pipeline** |
| POST | `/batches/{id}/cancel` | Cancel |
| POST | `/batches/{id}/retry` | Retry failed items |
| GET | `/batches/{id}/items` | Item-level status |
| GET | `/batches/{id}/stats` | Summary stats |
| GET | `/batches/{id}/download/pdf` | Download PDF |
| GET | `/batches/{id}/download/zip` | Download ZIP |

### Other (Tenants, Profiles, Subscriptions, Roles, Audit, Usage, Platform, Invites, Teams)
~56 additional endpoints for SaaS core operations.

### Stripe Webhooks

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/webhooks/stripe` | Stripe event handler |

> **Idempotency:** Webhook handler stores `stripe_event_id` in `subscription_events`
> with a **UNIQUE constraint**. Duplicate events are acknowledged (200) without
> reprocessing. Stripe signature is verified via `STRIPE_WEBHOOK_SECRET` before
> any processing.

---

## 6. Core Business Flows

### 6.1 Event Creation

```
POST /events {title, start_date, venue_*, vip_quota, normal_quota, ...}
  │
  ├── 1. Auth + Permission: events.create
  ├── 2. Auto-generate slug: "حفل-تخرج" → "حفل-تخرج-a3f2b1"
  ├── 3. INSERT INTO events (...) RETURNING *
  ├── 4. Audit log: event.create
  └── 5. Return EventRead
```

### 6.2 Invitation Creation (3 Modes)

```
┌─────────────────────────────────────────────────────────────────┐
│                    3 Creation Modes                              │
├──────────────────┬──────────────────┬───────────────────────────┤
│ POST /invitations│ POST /quick      │ POST /bulk-from-guests    │
│ (Standard)       │ (Quick)          │ (Bulk)                    │
├──────────────────┼──────────────────┼───────────────────────────┤
│ Single invite    │ By count or names│ From guest directory      │
│ Full details     │ Minimal details  │ Copies guest data         │
│ + Inline barcode │ No inline barcode│ Links guest_id            │
│ + Storage upload │ (batch later)    │ No inline barcode         │
└──────────────────┴──────────────────┴───────────────────────────┘
```

**Standard flow detail:**
```
1. Check quota (vip_quota / normal_quota)
2. INSERT → token auto-generated (32 hex bytes, UNIQUE)
3. Generate barcode inline:
   a. HMAC-SHA256(INVITE_HMAC_SECRET, invite_id:token)[:16] → signature
   b. QR content: https://domain/i/{token}
   c. Generate SVG (vector) + PNG (400px)
   d. Upload both to Supabase Storage
   e. UPDATE invitations SET barcode_svg_url, barcode_png_url, barcode_payload
4. Audit log
5. Return InvitationRead (with barcode URLs)
   * If barcode fails → invitation still created (graceful fallback)
```

### 6.3 Invitation Lifecycle (State Machine)

```
                    ┌──────────────────────────────────────────┐
                    │                                          │
  ┌─────────┐  send  ┌──────┐  open   ┌────────┐  accept  ┌──────────┐  scan  ┌────────────┐
  │ created ├───────→│ sent ├────────→│ viewed ├─────────→│ accepted ├──────→│ checked_in │
  └────┬────┘        └──┬───┘         └───┬────┘          └──────────┘       └────────────┘
       │                │                 │
       │                │                 │  decline  ┌──────────┐
       │                │                 └──────────→│ declined │
       │                │                             └──────────┘
       │                │
       ├────────────────┴─────────────────────────────→ revoked
       │
       └──────────────────────────────────────────────→ expired
```

### 6.4 Check-in Flow (Atomic)

```
POST /checkin/scan {token, event_id?, gate_id?}
  │
  ▼
┌─ DB: validate_checkin(token, event_id, gate_id) ─────────────┐
│                                                               │
│  SELECT ... FROM invitations i                                │
│  JOIN events e ON e.id = i.event_id                           │
│  WHERE i.token = p_token                                      │
│  FOR UPDATE OF i;  ← LOCKS the row (prevents race condition) │
│                                                               │
│  Checks (in order):                                           │
│  1. Token exists?           → invalid                         │
│  2. Correct event?          → wrong_event                     │
│  3. Revoked?                → revoked                         │
│  4. Expired?                → expired                         │
│  5. Already checked in?     → already_checked_in              │
│     (unless allow_reentry)                                    │
│  6. Gate allows this class? → wrong_gate                      │
│  7. ✅ UPDATE status='checked_in', checkin_count++            │
│     (inside same transaction = atomic)                        │
│                                                               │
│  Returns: invitation_id, result, guest_name, ticket_class     │
└───────────────────────────────────────────────────────────────┘
  │
  ▼
INSERT INTO checkins (every attempt logged, success or failure)
  │
  ▼
Return CheckinResponse {result, guest_name, ticket_class, message}
  Messages: ✅ تم تسجيل الدخول | ⚠️ مسبقاً | ❌ ملغاة | ❌ منتهية | ...
```

### 6.5 RSVP Flow (Public, No Auth)

```
POST /invitations/rsvp/{token} {status: "accepted", plus_one_count: 2, message: "..."}
  │
  ├── Lookup invitation by token
  ├── Check: not revoked/expired
  ├── Check: event.allow_rsvp = true
  ├── Check: event.allow_plus_one (for plus_one_count)
  ├── UPDATE: rsvp_status, rsvp_at, plus_one_count, status
  └── Return confirmation
```

---

## 7. Generation Pipeline

### 7.1 Pipeline Phases

```
POST /batches/{id}/start
  │
  ▼ Celery Task: batch.run_pipeline  (BackgroundTask fallback in dev only)
┌─ Phase 1: Barcodes (5→45%) ──────────────────────────────────┐
│  For each invitation:                                         │
│  ├── HMAC sign(invite_id, token) → signature                 │
│  ├── QR → SVG + PNG                                          │
│  ├── Upload → Supabase Storage                                │
│  ├── UPDATE invitations SET barcode_*_url, barcode_signature  │
│  └── UPDATE batch_items SET barcode_url, render_status        │
│  Commit every 50 items                                        │
└───────────────────────────────────────────────────────────────┘
  │
  ▼ (DESIGNED mode only)
┌─ Phase 2: Render Images (45→75%) ────────────────────────────┐
│  ├── Load background from Storage (once)                      │
│  ├── Load event data (once)                                   │
│  ├── For each invitation:                                     │
│  │   ├── Load guest data + custom_fields                      │
│  │   ├── Build context: {guest, event, invite, custom}        │
│  │   ├── For each template element:                           │
│  │   │   ├── Resolve data_key → text value                    │
│  │   │   ├── Arabic reshape + BiDi                            │
│  │   │   ├── Auto-fit: shrink → wrap → truncate "…"           │
│  │   │   └── Draw on canvas (Pillow)                          │
│  │   ├── Upload render → Storage                              │
│  │   ├── UPDATE invitations SET render_url                    │
│  │   └── UPDATE batch_items SET render_url, render_status     │
│  Commit every 20 items                                        │
└───────────────────────────────────────────────────────────────┘
  │
  ▼
┌─ Phase 3: PDF (75→85%) ──────────────────────────────────────┐
│  QUICK:    Grid N×M barcodes per page (A4/Letter/custom)      │
│  DESIGNED: One card per page                                  │
│  Upload → Storage                                             │
└───────────────────────────────────────────────────────────────┘
  │
  ▼
┌─ Phase 4: ZIP (85→95%) ──────────────────────────────────────┐
│  Files named: 0001__Ahmed_AlAli.png (sequential + sanitized)  │
│  Upload → Storage                                             │
└───────────────────────────────────────────────────────────────┘
  │
  ▼
┌─ Phase 5: Finalize (95→100%) ────────────────────────────────┐
│  Generate 5 preview images                                    │
│  Record metrics: duration_ms, pdf_size, zip_size              │
│  Record error_summary (JSONB)                                 │
│  SET status = 'ready', progress = 100                         │
└───────────────────────────────────────────────────────────────┘
```

### 7.2 Batch State Machine

```
draft ──→ queued ──→ generating_barcodes ──→ rendering_images ──→ generating_pdf
                                                                       │
                                                                       ▼
                                                                 generating_zip ──→ ready ■
                                                                       │
                                                                       ▼
Any state ──→ cancelled ■                                           (terminal)
Any running ──→ failed ──→ queued (retry)

■ = terminal state (no further transitions allowed)
Enforced by DB trigger: enforce_batch_transition
```

### 7.3 Reliability Features

| Feature | Implementation |
|---------|---------------|
| **Worker queue** | Celery + Redis: survives API restarts, autoscaling |
| **Idempotent** | Skips items where render_status = 'done' on restart |
| **Chunked commits** | Commit every 50 barcodes / 20 renders |
| **Per-item retry** | POST /batches/{id}/retry re-queues only failed items |
| **Graceful failure** | One item failing doesn't stop the batch |
| **Progress tracking** | Real-time progress 0-100% in DB |
| **Metrics** | duration_ms, pdf/zip sizes, error_summary |
| **Concurrency guard** | `pg_advisory_xact_lock` prevents double-start |
| **Time limits** | soft=30min, hard=35min, visibility=40min |
| **Rate limit** | 4 batches/min per Celery worker process (global, not per-tenant) |
| **Tempfile streaming** | ZIP written to disk, not RAM (prevents OOM) |

### 7.4 data_key Resolution

Template elements use `data_key` for dynamic content:

```
element_type: "guest_name"   → default data_key: "guest.name"
element_type: "event_title"  → default data_key: "event.title"
element_type: "custom_text"  → explicit data_key: "guest.custom_fields.seat"

Context structure:
{
  "guest":  { "name", "name_ar", "phone", "email", "custom_fields": {...} },
  "event":  { "title", "title_ar", "date", "time", "location" },
  "invite": { "code", "token", "barcode_payload", "ticket_class" },
  "custom": { "seat", "table", "gate", "hall", "zone", ...custom_fields }
}

Resolution: "guest.custom_fields.seat" → context["guest"]["custom_fields"]["seat"]
```

---

## 8. Security Model

### 8.1 Five Security Layers

```
Layer 1: Rate Limiting     → 3-tier: 30/min public, 300/min+burst checkin, 120/min global
Layer 2: JWT Auth           → Supabase Auth, token verification
Layer 3: RBAC Permissions   → 62 permission keys, checked per endpoint
Layer 4: Row-Level Security → PostgreSQL RLS on every table
Layer 5: HMAC Signatures    → Barcode payload integrity verification
```

> **Note:** API uses `service_role` which bypasses RLS (all operations). RLS protects
> non-service-role paths only (e.g., Supabase Realtime, direct client DB access).
> API tenant isolation relies on middleware tenant resolution + TenantQuery + DB
> tenant_id immutability trigger (see §4.5 Guardrails for full defense-in-depth).

### 8.2 HMAC Barcode Security

```
Signing:
  key     = INVITE_HMAC_SECRET (dedicated, NOT jwt_secret)
  message = f"{invite_id}:{token}"
  sig     = HMAC-SHA256(key, message).digest()[:16].hex()
            ─────────────────────────────────────────────
            16 bytes (128-bit) → 32 hex chars
            NOT hexdigest()[:16] which would be 64-bit only

  Output: 32 hex characters = 128-bit security strength
  Stored: invitations.barcode_signature (varchar)

Key Rotation:
  1. Set INVITE_HMAC_SECRET_PREV = current key
  2. Set INVITE_HMAC_SECRET = new key
  3. verify_signature tries current key first, then previous
  4. After all barcodes regenerated, clear _PREV

QR Content: https://domain/i/{token}
  → This is a Frontend route (not an API endpoint)
  → Frontend calls GET /invitations/view/{token} internally
  → Server looks up by token (indexed, O(1))
  → Validates status/event/gate
  → Logs every scan attempt

Purpose: Signature verification is performed server-side after token lookup
  to ensure the barcode payload matches the stored invitation record and to
  detect accidental corruption/mismatch in generation pipelines.
  Token entropy (128-bit) remains the primary anti-forgery control.
```

### 8.3 Rate Limiting (3-Tier)

| Tier | Endpoint Pattern | Auth | Limit | Reason |
|------|-----------------|------|-------|--------|
| **1** | `/invitations/view/{token}` | None (public) | 30/min | Token brute-force prevention |
| **1** | `/invitations/rsvp/{token}` | None (public) | 30/min | RSVP abuse prevention |
| **2** | `/checkin/scan` | **JWT** + `checkin.scan` | 300/min + burst 20/3s | High-throughput gate ops |
| **3** | Everything else | JWT + RBAC | 120/min | General protection |

> **Tier 2 rationale:** `/checkin/scan` requires JWT + `checkin.scan` permission
> (Check-in Staff role only). The 300/min limit supports real-world gate throughput
> (5 scans/sec sustained). Burst protection (20 requests in 3 seconds) prevents
> automated flooding while allowing normal queue processing at busy gates.
>
> **Rate limit key:** `ip + user_id` (from JWT). IP alone is insufficient at venues
> where multiple gate devices share a single NAT IP. Future enhancement: composite
> key `(tenant_id, event_id, gate_id, device_id)` via `X-Device-ID` header for
> per-device granularity.

### 8.4 Token Security

- **32 hex characters** (128 bits entropy) from `gen_random_bytes(16)`
- UNIQUE constraint in DB
- No tenant_id in token (prevents info leakage)
- Indexed for O(1) lookup

---

## 9. Services Architecture

### 9.1 barcode_service.py
- `sign_payload(invite_id, token)` → HMAC-SHA256 signature
- `verify_signature(invite_id, token, sig)` → tries current + previous key
- `generate_qr_svg(data)` → SVG bytes (vector, ~6KB)
- `generate_qr_png(data, size_px, colors)` → PNG bytes (~22KB)
- `generate_barcode_for_invitation(invite_id, token)` → full package

### 9.2 render_service.py
- `render_invitation_image(background, elements, context, w, h)` → PNG bytes
- `_auto_fit_text()` → 3 strategies: shrink → wrap 2 lines → truncate "…"
- `_reshape_arabic(text)` → arabic-reshaper + python-bidi
- `_resolve_data_key("guest.custom_fields.seat", context)` → value
- `_get_font(family, size, weight)` → cached font loading

### 9.3 pdf_service.py
- `generate_barcode_grid_pdf(items, layout)` → grid N×M per page
- `generate_cards_pdf(images, layout)` → one card per page
- Supports: A4, Letter, custom sizes, configurable margins/gaps/DPI

### 9.4 storage_service.py
- `upload_barcode_svg/png(tenant, event, invite, bytes)` → storage path
- `upload_render_image(tenant, event, invite, bytes)` → storage path
- `upload_batch_pdf/zip(tenant, event, batch, bytes)` → storage path
- `get_signed_url(path, expires_in)` → temporary download URL

**Storage path contract** (canonical — matches Appendix C):
```
{tenant_id}/{event_id}/barcodes/{invite_id}.svg
{tenant_id}/{event_id}/barcodes/{invite_id}.png
{tenant_id}/{event_id}/renders/{invite_id}.png
{tenant_id}/{event_id}/batches/{batch_id}/result.pdf
{tenant_id}/{event_id}/batches/{batch_id}/images.zip
{tenant_id}/{event_id}/batches/{batch_id}/preview_{0-4}.png
{tenant_id}/{event_id}/templates/{template_id}/background.{ext}
{tenant_id}/{event_id}/templates/{template_id}/assets/{filename}
```

> **Design decision:** Templates are **event-scoped** by design. Each event can have
> its own branding, layout, and assets. This avoids cross-event asset coupling and
> simplifies cleanup when an event is archived/deleted. If a tenant wants to reuse
> a template across events, they clone it (creating a new template_id per event).

### 9.5 batch_pipeline.py
- `run_batch_pipeline(db, batch_id)` → orchestrates 5 phases
- `_sanitize_filename(name, index)` → `0001__Ahmed_AlAli.png`
- `_build_render_context(inv, batch, event, guest)` → nested dict
- Tracks: duration_ms, pdf/zip sizes, error_summary (JSONB)

### 9.6 tenant_query.py (Option B Guardrail)
- `TenantQuery(db, tenant_id)` → enforced tenant-scoped query helper
- `select(table, columns, where, order_by, limit)` → auto `WHERE tenant_id = :tid`
- `select_one(table, columns, where)` → single row + tenant filter
- `update(table, set_clause, where)` → returns affected row count
- `delete(table, where)` → returns affected row count
- `insert(table, columns, values)` → auto-adds tenant_id if missing; rejects mismatch
- `count(table, where)` / `exists(table, where)` → tenant-scoped aggregates

### 9.7 permission_service.py
- `require_permission(db, tenant_id, user_id, key)` → raises 403
- Uses `user_has_permission()` DB function
- Owner/Admin bypass all checks

### 9.8 provisioning_service.py
- `provision_tenant(tenant_id, owner_id)` → creates:
  - 5 default roles (Admin, Member, Designer, Check-in Staff, Viewer)
  - Role ↔ Permission assignments
  - Default tenant settings (timezone, language, colors)

---

## 10. Data Models (Pydantic)

### 10.1 Event Models
- `EventCreate`: 30 fields (title, venue_*, quotas, settings)
- `EventRead`: 32 fields (+ id, slug, status, timestamps)
- `EventUpdate`: 26 fields (all Optional)
- `EventStats`: 9 counters (total, vip, sent, viewed, accepted, declined, checked_in, revoked)

### 10.2 Invitation Models
- `InvitationCreate`: 12 fields (event_id, guest details, seat, gate)
- `InvitationRead`: 27 fields (+ barcode URLs, render URL, RSVP, checkin)
- `QuickInviteCreate`: count OR names list
- `BulkInviteFromGuests`: guest_ids list
- `CheckinRequest/Response`: 7 result types with Arabic messages
- `RsvpRequest`: status, plus_one_count, message

### 10.3 Template Models
- `ElementCreate/Read/Update`: relative coords (0→1), data_key, font_asset_id
- 13 element types: guest_name, event_title, qr_code, barcode, custom_text, image...

### 10.4 Batch Models
- `LayoutConfig`: page_size (A4/Letter/custom), rows×cols, margins, gaps, DPI, barcode_render
- `BatchCreate`: event_id, mode (quick/designed), output_formats, layout
- `BatchRead`: + duration_ms, result_pdf_size, result_zip_size, error_summary

---

## 11. Middleware Stack

Execution order (last added = first executed):

```
1. CORSMiddleware          → Allow cross-origin requests
2. RateLimitMiddleware     → 120/min global + 30/min strict
3. SecurityHeadersMiddleware → nosniff, DENY, XSS protection
4. TenantResolutionMiddleware → Resolve tenant from request
```

### Tenant Resolution Priority
1. `X-Tenant-ID` header → direct UUID lookup
2. `X-Tenant-Slug` header → slug lookup
3. Subdomain → `amal.system.com` → slug="amal"
4. Custom domain → `app.amal.com` → tenant_domains lookup

### Exempt Paths (no tenant required)
`/health`, `/docs`, `/auth/*`, `/plans`, `/webhooks/stripe`, `/tenants`, `/platform`

> **Public endpoint governance:** The only truly public endpoints (no auth) are
> `/invitations/view/{token}` and `/invitations/rsvp/{token}`. These MUST execute
> single-row queries by token only, return only guest-safe fields, and use
> `WHERE id = :id AND token = :token` double-check on UPDATEs.
> `/checkin/scan` requires JWT + `checkin.scan` permission — it is NOT public.

---

## 12. Configuration & Environment

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...

# Database
DATABASE_URL=postgresql+asyncpg://postgres:pass@db.xxx.supabase.co:5432/postgres

# Stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# App
APP_URL=http://localhost:9000
APP_ENV=development

# Invitation Security (dedicated — do NOT reuse JWT secret)
INVITE_HMAC_SECRET=<64 hex chars>
INVITE_HMAC_SECRET_PREV=<previous key for rotation>
HMAC_ROTATION_DAYS=90

# Worker (Celery + Redis)
REDIS_URL=redis://localhost:6379/0
USE_WORKER=true   # false = BackgroundTask fallback (dev only)

# Storage
STORAGE_BUCKET=invitations
SIGNED_URL_EXPIRY=3600        # default signed URL (1h)
DOWNLOAD_URL_EXPIRY=604800    # batch downloads (7d)
```

---

## 13. Deployment & Migration Guide

### 13.1 Migration Order

```
1. supabase/schema_final.sql                       → SaaS core (17 tables)
2. supabase/fix_and_seed.sql                       → Patches
3. supabase/migration_v3_invitations_platform.sql  → Invitations (13 tables)
4. supabase/migration_v4_generation_batches.sql    → Batches (2 tables)
5. supabase/migration_v5_production_hardening.sql  → Atomic checkin + state machine
6. supabase/migration_v6_constraints_and_governance.sql → CHECK constraints + immutability
```

### 13.2 Supabase Storage Setup

1. Create bucket `invitations` (private)
2. Set max file size: 500MB
3. Service role has full access
4. **Never expose public URLs** — always use signed URLs with configurable expiry

### 13.3 Arabic Fonts

Download to `fonts/` directory:
- Cairo-Regular.ttf, Cairo-Bold.ttf (default Arabic fallback)
- Tajawal-Regular.ttf, Tajawal-Bold.ttf
- Amiri-Regular.ttf

Font fallback policy: `{"ar": "Cairo", "en": "Arial", "default": "Cairo"}`

### 13.4 Run API Server

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

### 13.5 Run Celery Worker (Production)

```bash
# Start Redis
redis-server

# Start worker (2 concurrent tasks)
celery -A app.worker worker --loglevel=info --concurrency=2

# Monitor (optional)
celery -A app.worker flower --port=5555
```

For development without Redis, set `USE_WORKER=false` in `.env`.

### 13.6 Plan Limits

| Limit Key | Free | Pro | Enterprise |
|-----------|------|-----|------------|
| events_per_month | 1 | 20 | Unlimited |
| invitations_per_event | 50 | 5,000 | Unlimited |
| invitations_per_month | 50 | 10,000 | Unlimited |
| teams_max | 1 | 5 | Unlimited |
| designed_templates | 0 | Unlimited | Unlimited |
| gates_per_event | 1 | 5 | Unlimited |

---

## Appendix A: Batch State Transitions

| From | Allowed To | Trigger |
|------|-----------|--------|
| `draft` | `queued`, `cancelled` | POST /start, POST /cancel |
| `queued` | `generating_barcodes`, `cancelled`, `failed` | Worker picks up, cancel, error |
| `generating_barcodes` | `rendering_images`, `generating_pdf`, `cancelled`, `failed` | Phase complete |
| `rendering_images` | `generating_pdf`, `cancelled`, `failed` | Phase complete |
| `generating_pdf` | `generating_zip`, `cancelled`, `failed` | Phase complete |
| `generating_zip` | `ready`, `cancelled`, `failed` | Phase complete |
| `ready` | _(terminal)_ | — |
| `failed` | `queued` | POST /retry |
| `cancelled` | _(terminal)_ | — |

Enforced by DB trigger: `enforce_batch_transition` (V5)

---

## Appendix B: Error Codes (Public vs Private)

| HTTP | Public Endpoints | Private Endpoints |
|------|-----------------|------------------|
| 400 | Validation error | Validation error |
| 401 | — (no auth) | Invalid/expired JWT |
| 403 | — | Insufficient permissions |
| 404 | الدعوة غير موجودة | Resource not found |
| 410 | الدعوة ملغاة/منتهية | — |
| 429 | Rate limit (30/min) | Rate limit (120/min) |
| 500 | Internal error | Internal error |

---

## Appendix C: Storage Paths Contract

```
{tenant_id}/{event_id}/barcodes/{invite_id}.svg
{tenant_id}/{event_id}/barcodes/{invite_id}.png
{tenant_id}/{event_id}/renders/{invite_id}.png
{tenant_id}/{event_id}/batches/{batch_id}/result.pdf
{tenant_id}/{event_id}/batches/{batch_id}/images.zip
{tenant_id}/{event_id}/batches/{batch_id}/preview_{0-4}.png
{tenant_id}/{event_id}/templates/{template_id}/background.{ext}
{tenant_id}/{event_id}/templates/{template_id}/assets/{filename}
```

All paths are private. Access via signed URLs only (configurable expiry).

---

## Appendix D: HMAC Key Rotation Procedure

```
1. Generate new key:  python -c "import secrets; print(secrets.token_hex(32))"
2. Set INVITE_HMAC_SECRET_PREV = current INVITE_HMAC_SECRET
3. Set INVITE_HMAC_SECRET = new key
4. Deploy → verify_signature() checks current then prev (grace period)
5. Schedule batch regeneration for all active events
6. After all barcodes regenerated, clear INVITE_HMAC_SECRET_PREV

Policy: rotate every 90 days (configurable via HMAC_ROTATION_DAYS)
Window: current + prev only (2-key maximum)
```

---

## Appendix E: LayoutConfig Spec

```json
{
  "page_size": "A4|Letter|custom",
  "orientation": "portrait|landscape",
  "rows": 5,           // 1-20
  "cols": 5,           // 1-20
  "margin_top_mm": 10,    // 0-100
  "margin_bottom_mm": 10, // 0-100
  "margin_left_mm": 10,   // 0-100
  "margin_right_mm": 10,  // 0-100
  "gap_x_mm": 2,       // 0-50
  "gap_y_mm": 2,       // 0-50
  "barcode_size_px": null, // 100-2000 or null (auto from cell size)
  "barcode_size_mode": "fit|contain",
  "show_code_text": true,
  "show_guest_name": true,
  "caption_field": "guest_name|code|none",
  "dpi": 300,          // 72-600
  "card_per_page": false,  // true for designed mode
  "custom_width_mm": null, // required if page_size=custom (50-1000)
  "custom_height_mm": null,// required if page_size=custom (50-1000)
  "barcode_render": "png|svg",
  "cell_padding_mm": 1    // 0-20
}
```

### Unit Conversion Formula

```
px = (mm / 25.4) × dpi
mm = (px × 25.4) / dpi

Example: 30mm cell at 300dpi = (30 / 25.4) × 300 = 354px
```

### barcode_size_px Auto-Calculation

When `barcode_size_px` is `null`, the system auto-calculates from cell dimensions:
```
page_w_mm = page width (A4=210, Letter=215.9, or custom_width_mm)
usable_w  = page_w - margin_left - margin_right - (gap_x × (cols-1))
cell_w_mm = (usable_w / cols) - (cell_padding × 2)
barcode_px = max(100, mm_to_px(cell_w_mm, dpi))
```

### Mode Defaults

- **quick** → `card_per_page=false`, grid N×M barcodes per page
- **designed** → `card_per_page=true`, 1 rendered card per page

---

## Appendix F: Font Governance

| Rule | Value |
|------|-------|
| Allowed extensions | `.ttf`, `.otf` only |
| WOFF/WOFF2 | **Not supported** — Pillow/FreeType cannot render at runtime |
| Max font file size | 5 MB |
| Magic byte validation | TTF (`\x00\x01\x00\x00`), OTF (`OTTO`), `true`, `typ1` |
| MIME constraint (DB) | `chk_font_mime` on template_assets |
| Size constraint (DB) | `chk_font_size` ≤ 5,242,880 bytes |
| Default fallback (Arabic) | Cairo |
| Default fallback (Latin) | Arial |
| Caching | In-memory per font_family+size+weight |

---

## Appendix G: Guest Data Snapshot Policy

When an invitation is created:
1. `guest_name`, `guest_phone`, `guest_email` are **copied** from the guest record
2. `guest_id` is stored as a reference link
3. If the guest record changes later, **existing invitations are NOT updated**
4. This is intentional: the invitation is a point-in-time snapshot for audit/print
5. To update invitation data, use `PATCH /invitations/{id}` explicitly

---

## Appendix H: SQL Constraints (V6)

| Table | Constraint | Rule |
|-------|-----------|------|
| `template_elements` | `chk_element_x` | `0 ≤ x ≤ 1` |
| `template_elements` | `chk_element_y` | `0 ≤ y ≤ 1` |
| `template_elements` | `chk_element_width` | `0 ≤ width ≤ 1` |
| `template_elements` | `chk_element_height` | `0 ≤ height ≤ 1` |
| `events` | `chk_vip_quota` | `vip_quota ≥ 0` |
| `events` | `chk_normal_quota` | `normal_quota ≥ 0` |
| `invitations` | `chk_checkin_count` | `checkin_count ≥ 0` |
| `template_assets` | `chk_font_mime` | TTF/OTF MIME whitelist (no WOFF) |
| `template_assets` | `chk_font_size` | font ≤ 5MB |
| `generation_batches` | `protect_ready_batch` | ready/cancelled = frozen results |
| `generation_batches` | `enforce_batch_transition` | valid state transitions only |
| **22 tables** | `prevent_*_tenant_change` | **tenant_id is immutable** (Option B guardrail) |

---

## Appendix I: Ops Checklist

- [ ] Run all 6 migrations in order
- [ ] Create `invitations` bucket (private, 500MB limit)
- [ ] Set `INVITE_HMAC_SECRET` (64 hex chars, NOT jwt secret)
- [ ] Set `REDIS_URL` and start Redis
- [ ] Start Celery worker: `celery -A app.worker worker --concurrency=2`
- [ ] Download Arabic fonts to `fonts/`
- [ ] Configure Stripe webhook → `/api/v1/webhooks/stripe`
- [ ] Set `APP_URL` to production domain
- [ ] Set `APP_ENV=production`
- [ ] Restrict CORS origins in `main.py`
- [ ] Schedule HMAC key rotation (every 90 days)
- [ ] Monitor: batch duration_ms, error_summary, worker health

---

## Summary Statistics (Current Snapshot)

| Metric | Value |
|--------|-------|
| Database Tables | 34 |
| RLS Policies | 75+ |
| Permissions | 62 |
| DB Functions | 19 |
| DB Triggers | 28 |
| CHECK Constraints | 11 |
| API Endpoints | 120 |
| Route Files | 14 |
| Service Files | 13 |
| Model Files | 7 |
| Invitation States | 8 |
| Batch States | 9 |
| Check-in Results | 7 |
| Element Types | 13 |
| Default Roles | 5 |
| SQL Migrations | 6 |
