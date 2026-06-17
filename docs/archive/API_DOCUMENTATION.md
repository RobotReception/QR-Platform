# Digital Invitations Platform — API Documentation

> **Version:** v4.1 Final · **Base URL:** `https://api.yourdomain.com/api/v1`
> **Total Endpoints:** 120 · **Auth:** JWT (Supabase Auth) · **Format:** JSON
> **Last Updated:** February 2026

---

## Table of Contents

1. [General Information](#1-general-information)
2. [Authentication (8 endpoints)](#2-authentication)
3. [Profile (2 endpoints)](#3-profile)
4. [Tenants (16 endpoints)](#4-tenants)
5. [Events (12 endpoints)](#5-events)
6. [Digital Invitations (13 endpoints)](#6-digital-invitations)
7. [Check-in (4 endpoints)](#7-check-in)
8. [Templates (12 endpoints)](#8-templates)
9. [Guests (6 endpoints)](#9-guests)
10. [Generation Batches (10 endpoints)](#10-generation-batches)
11. [Roles & Permissions (8 endpoints)](#11-roles--permissions)
12. [Team Invites (4 endpoints)](#12-team-invites)
13. [Teams (8 endpoints)](#13-teams)
14. [Subscriptions & Plans (5 endpoints)](#14-subscriptions--plans)
15. [Usage & Limits (1 endpoint)](#15-usage--limits)
16. [Audit Logs (1 endpoint)](#16-audit-logs)
17. [Platform Admin (6 endpoints)](#17-platform-admin)
18. [Webhooks (1 endpoint)](#18-webhooks)
19. [Enums & Constants](#19-enums--constants)
20. [Error Codes](#20-error-codes)

---

## 1. General Information

### Authentication

All endpoints (except those marked **Public**) require a JWT token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Tenant Context

Most endpoints require a tenant context via the `X-Tenant-ID` header:

```
X-Tenant-ID: <uuid>
```

Endpoints that do NOT require this header are marked with 🌐 (Global).

### Pagination

List endpoints support:
| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | int | 50–100 | 200–1000 | Items per page |
| `offset` | int | 0 | — | Skip N items |

### Standard Response Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | Deleted (no body) |
| `400` | Bad request / validation error |
| `401` | Not authenticated |
| `403` | Forbidden (no permission) |
| `404` | Not found |
| `409` | Conflict (duplicate) |
| `429` | Rate limit exceeded |

### Rate Limiting

| Tier | Endpoints | Limit | Auth |
|------|-----------|-------|------|
| Public | `/invitations/view/{token}`, `/invitations/rsvp/{token}` | 30/min | None |
| Check-in | `/checkin/scan` | 300/min + burst 20/3s | JWT |
| Global | Everything else | 120/min | JWT |

---

## 2. Authentication

> 🌐 No `X-Tenant-ID` required for auth endpoints.

### 2.1 Sign Up

```
POST /auth/signup
```

Creates a new user account. Sends verification + welcome emails.

**Request Body:**
```json
{
  "email": "user@example.com",       // required, valid email
  "password": "SecureP@ss123",       // required, min 6 chars
  "full_name": "أحمد العلي"          // optional
}
```

**Response:** `201 Created`
```json
{
  "message": "تم التسجيل بنجاح. يرجى تأكيد بريدك الإلكتروني.",
  "user_id": "uuid",
  "access_token": null,
  "refresh_token": null,
  "tenants": null,
  "requires_tenant_selection": false
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `409` | البريد الإلكتروني مسجل مسبقاً |
| `400` | فشل التسجيل |

---

### 2.2 Login

```
POST /auth/login
```

Authenticates user. If user belongs to multiple tenants, returns tenant list for selection.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecureP@ss123",
  "tenant_id": "uuid"               // optional — pre-select tenant
}
```

**Response:** `200 OK`
```json
{
  "message": "تم تسجيل الدخول بنجاح",
  "user_id": "uuid",
  "access_token": "eyJ...",
  "refresh_token": "abc...",
  "tenants": [
    {
      "tenant_id": "uuid",
      "slug": "my-org",
      "name": "My Organization",
      "tenant_status": "active",
      "plan": "pro",
      "role": "owner",
      "membership_status": "active"
    }
  ],
  "requires_tenant_selection": false
}
```

> **Frontend Note:** If `requires_tenant_selection` is `true`, show a tenant picker UI before proceeding. The `access_token` is still valid — use it with the selected `X-Tenant-ID`.

**Errors:**
| Code | Detail |
|------|--------|
| `401` | بيانات الدخول غير صحيحة |

---

### 2.3 Request Password Reset

```
POST /auth/password-reset/request
```

Sends a password reset link to the email. **Always returns success** (prevents email enumeration).

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "إذا كان البريد الإلكتروني مسجلاً، ستصلك رسالة لإعادة تعيين كلمة المرور."
}
```

---

### 2.4 Confirm Password Reset

```
POST /auth/password-reset/confirm
```

Resets password using the token from the reset email link.

**Request Body:**
```json
{
  "access_token": "token-from-email-link",
  "new_password": "NewSecureP@ss456"
}
```

**Response:** `200 OK`
```json
{
  "message": "تم إعادة تعيين كلمة المرور بنجاح. يمكنك تسجيل الدخول الآن.",
  "user_id": "uuid"
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `400` | رمز غير صالح أو منتهي الصلاحية |

---

### 2.5 Change Password

```
POST /auth/change-password
```

🔒 **Auth required.** Changes password for the currently logged-in user.

**Request Body:**
```json
{
  "current_password": "OldP@ss123",
  "new_password": "NewP@ss456"
}
```

**Response:** `200 OK`
```json
{
  "message": "تم تغيير كلمة المرور بنجاح",
  "user_id": "uuid"
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `401` | كلمة المرور الحالية غير صحيحة |

---

### 2.6 Refresh Token

```
POST /auth/refresh
```

Refreshes an expired access token using the refresh token.

**Request Body:**
```json
{
  "refresh_token": "abc..."
}
```

**Response:** `200 OK`
```json
{
  "message": "تم تحديث التوكن بنجاح",
  "user_id": "uuid",
  "access_token": "eyJ...(new)",
  "refresh_token": "xyz...(new)"
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `401` | رمز التحديث غير صالح أو منتهي الصلاحية |

---

### 2.7 Logout

```
POST /auth/logout
```

🔒 **Auth required.** Signs out the user (invalidates refresh token).

**Response:** `200 OK`
```json
{
  "message": "تم تسجيل الخروج بنجاح"
}
```

---

### 2.8 Get Current User

```
GET /auth/me
```

🔒 **Auth required.** Returns current user info + profile + list of tenants with roles. **This is the main endpoint the frontend calls after login.**

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "full_name": "أحمد العلي",
  "avatar_url": "https://...",
  "phone": "+966...",
  "is_staff": false,
  "status": "active",
  "email_verified_at": "2026-01-15T10:00:00",
  "last_login_at": "2026-02-10T14:00:00",
  "created_at": "2026-01-01T00:00:00",
  "tenants": [
    {
      "tenant_id": "uuid",
      "slug": "my-org",
      "name": "My Organization",
      "tenant_status": "active",
      "plan": "pro",
      "role": "owner",
      "membership_status": "active"
    }
  ]
}
```

> **Frontend Flow:**
> 1. Call `POST /auth/login` → get tokens
> 2. Call `GET /auth/me` → get user profile + tenants list
> 3. If multiple tenants → show tenant picker
> 4. Set `X-Tenant-ID` header for all subsequent requests

---

## 3. Profile

> 🌐 No `X-Tenant-ID` required.

### 3.1 Get My Profile

```
GET /profile/me
```

🔒 **Auth required.**

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "full_name": "أحمد العلي",
  "avatar_url": "https://...",
  "phone": "+966501234567",
  "is_staff": false,
  "status": "active",
  "email_verified_at": "2026-01-15T10:00:00",
  "last_login_at": "2026-02-10T14:00:00",
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-02-10T14:00:00"
}
```

---

### 3.2 Update My Profile

```
PATCH /profile/me
```

🔒 **Auth required.** Partial update — send only the fields you want to change.

**Request Body (all optional):**
```json
{
  "full_name": "أحمد محمد العلي",
  "avatar_url": "https://...",
  "phone": "+966509876543"
}
```

**Response:** `200 OK` — Returns updated `ProfileRead`.

---

## 4. Tenants

### 4.1 Create Tenant

```
POST /tenants
```

🔒 **Auth required.** 🌐 No `X-Tenant-ID`.
Creates a new organization. The creator becomes the **owner**. Automatically provisions:
- 5 default roles (Admin, Member, Designer, Check-in Staff, Viewer)
- Role ↔ Permission assignments
- Default tenant settings
- Free trial subscription (14 days)

**Request Body:**
```json
{
  "slug": "my-company",              // required, unique, URL-safe
  "name": "شركتي",                   // required
  "metadata": {}                     // optional
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "slug": "my-company",
  "name": "شركتي",
  "created_by": "uuid",
  "status": "trial",
  "plan": "free",
  "metadata": {},
  "expires_at": null,
  "created_at": "2026-02-10T14:00:00",
  "updated_at": "2026-02-10T14:00:00"
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `409` | Slug already taken |

---

### 4.2 List My Tenants

```
GET /tenants
```

🔒 **Auth required.** 🌐 No `X-Tenant-ID`.
Returns all tenants the current user belongs to.

**Response:** `200 OK` — Array of `TenantRead`.

---

### 4.3 Get Current Tenant

```
GET /tenants/current
```

🔒 **Auth required.** Returns details of the tenant specified in `X-Tenant-ID`.

**Response:** `200 OK` — `TenantRead` object.

---

### 4.4 Update Current Tenant

```
PATCH /tenants/current
```

🔒 **Auth required.** 🛡️ **Permission:** Admin role.

**Request Body (all optional):**
```json
{
  "name": "اسم جديد",
  "slug": "new-slug"
}
```

**Response:** `200 OK` — Updated `TenantRead`.

---

### 4.5 List Members

```
GET /tenants/current/members
```

🔒 **Auth required.** 🛡️ **Permission:** `members.view`

**Response:** `200 OK`
```json
[
  {
    "tenant_id": "uuid",
    "user_id": "uuid",
    "role": "owner",
    "status": "active",
    "created_at": "2026-01-01T00:00:00",
    "full_name": "أحمد العلي",
    "avatar_url": "https://..."
  }
]
```

---

### 4.6 Update Member

```
PATCH /tenants/current/members/{member_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `members.manage`
Cannot change your own role.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `member_id` | UUID | User ID of the member |

**Request Body (all optional):**
```json
{
  "role": "admin",
  "status": "active"
}
```

**Response:** `200 OK` — `MembershipRead`.

---

### 4.7 Remove Member

```
DELETE /tenants/current/members/{member_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `members.manage`
Cannot remove yourself.

**Response:** `204 No Content`

---

### 4.8 List Settings

```
GET /tenants/current/settings
```

🔒 **Auth required.** 🛡️ **Permission:** `settings.view`

**Response:** `200 OK`
```json
[
  {
    "tenant_id": "uuid",
    "key": "timezone",
    "value": "Asia/Riyadh",
    "updated_at": "2026-01-01T00:00:00"
  }
]
```

---

### 4.9 Upsert Setting

```
PUT /tenants/current/settings
```

🔒 **Auth required.** 🛡️ **Permission:** `settings.manage`

**Request Body:**
```json
{
  "key": "timezone",
  "value": "Asia/Riyadh"
}
```

**Response:** `200 OK` — `TenantSettingRead`.

---

### 4.10 List Custom Domains

```
GET /tenants/current/domains
```

🔒 **Auth required.** 🛡️ **Permission:** `settings.view`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "domain": "app.mycompany.com",
    "is_primary": true,
    "is_verified": false,
    "created_at": "2026-02-10T14:00:00"
  }
]
```

---

### 4.11 Add Custom Domain

```
POST /tenants/current/domains
```

🔒 **Auth required.** 🛡️ **Permission:** `settings.manage`

**Request Body:**
```json
{
  "domain": "app.mycompany.com",
  "is_primary": true
}
```

**Response:** `201 Created` — `TenantDomainRead`.

**Errors:**
| Code | Detail |
|------|--------|
| `409` | هذا النطاق مسجل مسبقاً |

---

### 4.12 Remove Custom Domain

```
DELETE /tenants/current/domains/{domain_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `settings.manage`

**Response:** `204 No Content`

---

### 4.13 List Feature Flags

```
GET /tenants/current/features
```

🔒 **Auth required.** (Membership check only)

**Response:** `200 OK`
```json
[
  {
    "tenant_id": "uuid",
    "flag_key": "dark_mode",
    "enabled": true,
    "metadata": null,
    "updated_at": "2026-02-10T14:00:00"
  }
]
```

---

### 4.14 Toggle Feature Flag

```
PUT /tenants/current/features/{flag_key}?enabled=true
```

🔒 **Auth required.** 🛡️ **Permission:** `features.manage`

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Enable or disable |

**Response:** `200 OK` — Feature flag object.

---

## 5. Events

### 5.1 Create Event

```
POST /events
```

🔒 **Auth required.** 🛡️ **Permission:** `events.create`

**Request Body:**
```json
{
  "title": "حفل تخرج 2026",                    // required
  "title_ar": "حفل تخرج ٢٠٢٦",                 // optional
  "description": "...",                          // optional
  "event_type_id": "uuid",                      // optional
  "category_id": "uuid",                        // optional
  "start_date": "2026-06-15T18:00:00",          // required
  "end_date": "2026-06-15T23:00:00",            // optional
  "timezone": "Asia/Riyadh",                     // optional
  "venue_name": "فندق الريتز",                   // optional
  "venue_name_ar": "فندق الريتز",                // optional
  "venue_address": "...",                        // optional
  "venue_city": "الرياض",                        // optional
  "venue_country": "SA",                         // optional
  "venue_map_url": "https://maps...",            // optional
  "venue_lat": 24.7136,                          // optional
  "venue_lng": 46.6753,                          // optional
  "vip_quota": 100,                              // optional, 0 = unlimited
  "normal_quota": 500,                           // optional, 0 = unlimited
  "allow_rsvp": true,                            // optional
  "allow_plus_one": true,                        // optional
  "allow_reentry": false,                        // optional
  "require_name": true,                          // optional
  "cover_image_url": "https://...",              // optional
  "theme_color": "#1a73e8",                      // optional
  "team_id": "uuid",                             // optional
  "metadata": {}                                 // optional
}
```

**Response:** `201 Created` — Full `EventRead` object with auto-generated `slug`.

> **Frontend Note:** The `slug` is auto-generated from the title (e.g., `"حفل-تخرج-a3f2b1"`).

---

### 5.2 List Events

```
GET /events?status=published
```

🔒 **Auth required.** 🛡️ **Permission:** `events.view`

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter: `draft`, `published`, `completed`, `cancelled` |

**Response:** `200 OK` — Array of `EventRead`, ordered by `start_date DESC`.

---

### 5.3 Get Event

```
GET /events/{event_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `events.view`

**Response:** `200 OK` — `EventRead`.

---

### 5.4 Update Event

```
PATCH /events/{event_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `events.edit`
Partial update — send only changed fields.

**Request Body:** Same fields as Create (all optional).

**Response:** `200 OK` — Updated `EventRead`.

---

### 5.5 Delete Event

```
DELETE /events/{event_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `events.delete`

**Response:** `204 No Content`

> ⚠️ **Warning:** Deleting an event cascades to all invitations, batches, check-ins, and templates linked to it.

---

### 5.6 Publish Event

```
POST /events/{event_id}/publish
```

🔒 **Auth required.** 🛡️ **Permission:** `events.publish`
Transitions event from `draft` → `published`.

**Response:** `200 OK` — Updated `EventRead` with `status: "published"`.

**Errors:**
| Code | Detail |
|------|--------|
| `400` | الحدث غير موجود أو تم نشره مسبقاً |

---

### 5.7 Get Event Stats

```
GET /events/{event_id}/stats
```

🔒 **Auth required.** 🛡️ **Permission:** `events.view`

**Response:** `200 OK`
```json
{
  "total_invitations": 600,
  "vip_count": 100,
  "normal_count": 500,
  "sent_count": 450,
  "viewed_count": 320,
  "accepted_count": 280,
  "declined_count": 15,
  "checked_in_count": 200,
  "revoked_count": 5
}
```

> **Frontend Note:** Use this for the event dashboard. Good for charts/counters.

---

### 5.8 List Event Categories

```
GET /events/categories
```

🔒 **Auth required.**

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "tenant_id": null,
    "name": "Wedding",
    "name_ar": "زفاف",
    "icon": "💍",
    "color": "#e91e63",
    "sort_order": 1,
    "is_system": true,
    "created_at": "..."
  }
]
```

---

### 5.9 Create Event Category

```
POST /events/categories
```

🔒 **Auth required.** 🛡️ **Permission:** `events.create`

**Request Body:**
```json
{
  "name": "Conference",
  "name_ar": "مؤتمر",
  "icon": "🎤",
  "color": "#2196f3"
}
```

**Response:** `201 Created` — `EventCategoryRead`.

---

### 5.10 List Event Types

```
GET /events/types?category_id=uuid
```

🔒 **Auth required.**

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `category_id` | UUID | Optional — filter by category |

**Response:** `200 OK` — Array of `EventTypeRead`.

---

### 5.11 List Event Gates

```
GET /events/{event_id}/gates
```

🔒 **Auth required.** 🛡️ **Permission:** `gates.view`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "event_id": "uuid",
    "name": "Main Gate",
    "name_ar": "البوابة الرئيسية",
    "allowed_classes": ["vip", "normal"],
    "created_at": "..."
  }
]
```

> **Frontend Note:** Gates are used in check-in to validate that the guest's ticket class is allowed at a specific gate.

---

### 5.12 Create Event Gate

```
POST /events/{event_id}/gates
```

🔒 **Auth required.** 🛡️ **Permission:** `gates.manage`

**Request Body:**
```json
{
  "name": "VIP Entrance",
  "name_ar": "مدخل كبار الشخصيات",
  "allowed_classes": ["vip"]
}
```

**Response:** `201 Created` — `EventGateRead`.

---

### 5.13 Delete Event Gate

```
DELETE /events/{event_id}/gates/{gate_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `gates.manage`

**Response:** `204 No Content`

---

## 6. Digital Invitations

### 6.1 List Invitations

```
GET /invitations?event_id=uuid&status=sent&ticket_class=vip&limit=100&offset=0
```

🔒 **Auth required.** 🛡️ **Permission:** `invitations.view`

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | Filter by event |
| `status` | string | `created`, `sent`, `viewed`, `accepted`, `declined`, `checked_in`, `revoked`, `expired` |
| `ticket_class` | string | `vip` or `normal` |
| `limit` | int | Max 500, default 100 |
| `offset` | int | Pagination offset |

**Response:** `200 OK` — Array of `InvitationRead`.

---

### 6.2 Get Invitation

```
GET /invitations/{invitation_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `invitations.view`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "event_id": "uuid",
  "template_id": "uuid",
  "guest_id": "uuid",
  "token": "a1b2c3d4e5f6...",
  "ticket_class": "vip",
  "status": "sent",
  "guest_name": "أحمد العلي",
  "guest_name_ar": "أحمد العلي",
  "guest_phone": "+966501234567",
  "guest_email": "ahmed@example.com",
  "seat_number": "A12",
  "table_number": "5",
  "gate_id": "uuid",
  "hall": "القاعة الكبرى",
  "zone": "VIP",
  "barcode_svg_url": "https://signed-url...",
  "barcode_png_url": "https://signed-url...",
  "barcode_payload": "https://domain/i/a1b2c3...",
  "barcode_signature": "32-hex-chars",
  "render_image_url": "https://signed-url...",
  "card_image_url": "https://signed-url...",
  "qr_data": "https://domain/i/a1b2c3...",
  "rsvp_status": "accepted",
  "rsvp_at": "2026-02-08T10:00:00",
  "plus_one_count": 2,
  "rsvp_message": "سعيد بالحضور",
  "checkin_count": 1,
  "checked_in_at": "2026-02-10T18:30:00",
  "checked_in_by": "uuid",
  "notes": "...",
  "metadata": {},
  "created_by": "uuid",
  "created_at": "2026-02-01T12:00:00",
  "updated_at": "2026-02-10T18:30:00"
}
```

---

### 6.3 Create Invitation (Standard)

```
POST /invitations
```

🔒 **Auth required.** 🛡️ **Permission:** `invitations.create`
Creates a single invitation with **inline barcode generation** (QR SVG + PNG uploaded to storage).

**Request Body:**
```json
{
  "event_id": "uuid",                           // required
  "template_id": "uuid",                        // optional
  "guest_id": "uuid",                           // optional — link to guest directory
  "ticket_class": "vip",                        // required: "vip" | "normal"
  "guest_name": "أحمد العلي",                    // optional
  "guest_name_ar": "أحمد العلي",                 // optional
  "guest_phone": "+966501234567",                // optional
  "guest_email": "ahmed@example.com",            // optional
  "seat_number": "A12",                          // optional
  "table_number": "5",                           // optional
  "gate_id": "uuid",                             // optional
  "hall": "القاعة الكبرى",                        // optional
  "zone": "VIP",                                 // optional
  "notes": "...",                                // optional
  "metadata": {}                                 // optional
}
```

**Response:** `201 Created` — `InvitationRead` (includes barcode URLs).

**Errors:**
| Code | Detail |
|------|--------|
| `400` | تم الوصول للحد الأقصى لدعوات vip (100) |
| `404` | الحدث غير موجود |

> **Frontend Note:** After creation, `barcode_svg_url` and `barcode_png_url` are immediately available. If barcode generation fails, the invitation is still created (URLs will be null — generate later via batch).

---

### 6.4 Create Quick Invitations

```
POST /invitations/quick
```

🔒 **Auth required.** 🛡️ **Permission:** `invitations.create`
Creates multiple invitations at once — by count or by names list. No inline barcode (use batch generation later).

**Request Body:**
```json
{
  "event_id": "uuid",                           // required
  "ticket_class": "normal",                     // required
  "template_id": "uuid",                        // optional
  "gate_id": "uuid",                            // optional
  "count": 50,                                  // option A: create N unnamed invitations
  "names": ["أحمد", "محمد", "فاطمة"]            // option B: create named invitations
}
```

> Provide either `count` OR `names`, not both.

**Response:** `201 Created`
```json
{
  "created": 50,
  "invitations": [
    { "id": "uuid", "token": "abc...", "guest_name": null, "ticket_class": "normal", "status": "created" }
  ]
}
```

---

### 6.5 Create Bulk from Guest Directory

```
POST /invitations/bulk-from-guests
```

🔒 **Auth required.** 🛡️ **Permission:** `invitations.create`
Creates invitations from existing guest records. Copies guest data (name, phone, email) into the invitation.

**Request Body:**
```json
{
  "event_id": "uuid",                           // required
  "ticket_class": "vip",                        // required
  "template_id": "uuid",                        // optional
  "gate_id": "uuid",                            // optional
  "guest_ids": ["uuid1", "uuid2", "uuid3"]      // required
}
```

**Response:** `201 Created`
```json
{
  "created": 3
}
```

---

### 6.6 Update Invitation

```
PATCH /invitations/{invitation_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `invitations.create`
Partial update — change seat, gate, notes, etc.

**Request Body (all optional):**
```json
{
  "guest_name": "أحمد محمد",
  "seat_number": "B5",
  "gate_id": "uuid",
  "notes": "Updated notes"
}
```

**Response:** `200 OK` — Updated `InvitationRead`.

---

### 6.7 Revoke Invitation

```
POST /invitations/{invitation_id}/revoke
```

🔒 **Auth required.** 🛡️ **Permission:** `invitations.revoke`
Sets status to `revoked`. Cannot revoke already revoked/expired invitations.

**Response:** `200 OK`
```json
{
  "message": "تم إلغاء الدعوة"
}
```

---

### 6.8 Bulk Revoke

```
POST /invitations/bulk-revoke
```

🔒 **Auth required.** 🛡️ **Permission:** `invitations.revoke`

**Request Body:**
```json
{
  "invitation_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response:** `200 OK`
```json
{
  "revoked": 3
}
```

---

### 6.9 Send Invitations

```
POST /invitations/send
```

🔒 **Auth required.** 🛡️ **Permission:** `invitations.send`
Sends invitations via the specified channel and updates status to `sent`.

**Request Body:**
```json
{
  "invitation_ids": ["uuid1", "uuid2"],
  "channel": "whatsapp"                         // "whatsapp" | "sms" | "email" | "link"
}
```

**Response:** `200 OK`
```json
{
  "sent": 2
}
```

---

### 6.10 View Invitation (Public)

```
GET /invitations/view/{token}
```

🌐 **Public — No auth required.** Rate limited: 30/min.
Returns guest-safe fields only. Marks invitation as `viewed` on first access.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `token` | string | 32-char hex token from QR/link |

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "token": "a1b2c3...",
  "status": "viewed",
  "ticket_class": "vip",
  "guest_name": "أحمد العلي",
  "guest_name_ar": "أحمد العلي",
  "seat_number": "A12",
  "table_number": "5",
  "hall": "القاعة الكبرى",
  "zone": "VIP",
  "barcode_png_url": "https://...",
  "render_image_url": "https://...",
  "card_image_url": "https://...",
  "qr_data": "https://domain/i/a1b2c3...",
  "rsvp_status": null,
  "plus_one_count": 0,
  "event_title": "حفل تخرج 2026",
  "event_title_ar": "حفل تخرج ٢٠٢٦",
  "start_date": "2026-06-15T18:00:00",
  "end_date": "2026-06-15T23:00:00",
  "venue_name": "فندق الريتز",
  "venue_name_ar": "فندق الريتز",
  "venue_address": "...",
  "venue_map_url": "https://maps...",
  "venue_lat": 24.7136,
  "venue_lng": 46.6753,
  "allow_rsvp": true,
  "allow_plus_one": true,
  "cover_image_url": "https://..."
}
```

> **Frontend Note:** This is the data for the **public invitation page** (`/i/{token}`). Use `cover_image_url` as hero, `card_image_url` or `render_image_url` as the designed card, and show RSVP form if `allow_rsvp` is true.

**Errors:**
| Code | Detail |
|------|--------|
| `404` | الدعوة غير موجودة |
| `410` | تم إلغاء هذه الدعوة |

---

### 6.11 RSVP (Public)

```
POST /invitations/rsvp/{token}
```

🌐 **Public — No auth required.** Rate limited: 30/min.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `token` | string | 32-char hex token |

**Request Body:**
```json
{
  "status": "accepted",                         // "accepted" | "declined"
  "plus_one_count": 2,                          // optional, only if event allows
  "message": "سعيد بالحضور"                     // optional
}
```

**Response:** `200 OK`
```json
{
  "message": "تم تسجيل ردك بنجاح",
  "rsvp_status": "accepted"
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `404` | الدعوة غير موجودة |
| `410` | الدعوة ملغاة أو منتهية |
| `400` | RSVP غير مفعّل لهذا الحدث |

---

## 7. Check-in

### 7.1 QR Scan Check-in

```
POST /checkin/scan
```

🔒 **Auth required.** 🛡️ **Permission:** `checkin.scan`
Rate limit: **300/min + burst 20/3s** (high-throughput gate operations).

**Request Body:**
```json
{
  "token": "a1b2c3d4...",                       // required — from QR scan
  "event_id": "uuid",                           // optional — validates correct event
  "gate_id": "uuid",                            // optional — validates gate access
  "scan_method": "qr",                          // optional: "qr" | "manual"
  "device_info": "iPhone 15 Pro"                // optional
}
```

**Response:** `200 OK`
```json
{
  "invitation_id": "uuid",
  "result": "success",
  "guest_name": "أحمد العلي",
  "ticket_class": "vip",
  "event_title": "حفل تخرج 2026",
  "checkin_count": 1,
  "message": "✅ تم تسجيل الدخول بنجاح"
}
```

**Possible `result` values:**

| Result | Message | Color |
|--------|---------|-------|
| `success` | ✅ تم تسجيل الدخول بنجاح | 🟢 Green |
| `already_checked_in` | ⚠️ تم تسجيل الدخول مسبقاً | 🟡 Yellow |
| `revoked` | ❌ الدعوة ملغاة | 🔴 Red |
| `expired` | ❌ الدعوة منتهية الصلاحية | 🔴 Red |
| `wrong_event` | ❌ الدعوة لحدث آخر | 🔴 Red |
| `wrong_gate` | ❌ البوابة غير مسموحة لهذا النوع | 🔴 Red |
| `invalid` | ❌ رمز غير صالح | 🔴 Red |

> **Frontend Note:** Build a full-screen check-in UI with camera QR scanner. Show the result with the appropriate color and play a sound. Display `guest_name` and `ticket_class` prominently.

---

### 7.2 Manual Check-in

```
POST /checkin/manual?invitation_id=uuid&gate_id=uuid
```

🔒 **Auth required.** 🛡️ **Permission:** `checkin.manual`
Check-in by invitation ID (without QR scan). Uses the same validation logic as scan.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `invitation_id` | UUID | Required |
| `gate_id` | UUID | Optional |

**Response:** Same as QR Scan Check-in.

---

### 7.3 Check-in History

```
GET /checkin/history?event_id=uuid&result=success&limit=100
```

🔒 **Auth required.** 🛡️ **Permission:** `checkin.view`

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | Filter by event |
| `result` | string | Filter: `success`, `already_checked_in`, `invalid`, etc. |
| `limit` | int | Max 500, default 100 |

**Response:** `200 OK` — Array of `CheckinRead`.

---

### 7.4 Live Check-in Stats

```
GET /checkin/live/{event_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `checkin.view`

**Response:** `200 OK`
```json
{
  "stats": {
    "checked_in": 200,
    "vip_checked_in": 45,
    "normal_checked_in": 155,
    "total_valid": 595,
    "total_vip": 100,
    "total_normal": 495
  },
  "recent_checkins": [
    {
      "created_at": "2026-02-10T18:30:00",
      "result": "success",
      "guest_name": "أحمد العلي",
      "ticket_class": "vip",
      "scan_method": "qr"
    }
  ]
}
```

> **Frontend Note:** Use this for a **live dashboard** at the event. Poll every 5–10 seconds. Show progress bars (checked_in / total_valid), VIP vs Normal breakdown, and a scrolling feed of recent check-ins.

---

## 8. Templates

### 8.1 List Templates

```
GET /templates?event_id=uuid
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.view`

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | Optional — filter by event (also returns shared templates) |

**Response:** `200 OK` — Array of `TemplateRead`.

---

### 8.2 Create Template

```
POST /templates
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.create`

**Request Body:**
```json
{
  "name": "بطاقة VIP ذهبية",                    // required
  "event_id": "uuid",                           // optional — null = shared template
  "template_type": "designed",                   // "designed" | "quick"
  "ticket_class": "vip",                        // "vip" | "normal" | "all"
  "width_px": 1080,                             // required
  "height_px": 1920,                            // required
  "orientation": "portrait",                    // "portrait" | "landscape"
  "background_url": null,                       // optional — set via upload
  "background_color": "#1a1a2e",                // optional
  "quick_style": {},                            // optional — for quick mode
  "is_default": false,                          // optional
  "metadata": {}                                // optional
}
```

**Response:** `201 Created` — `TemplateRead`.

---

### 8.3 Get Template

```
GET /templates/{template_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.view`

**Response:** `200 OK` — `TemplateRead`.

---

### 8.4 Update Template

```
PATCH /templates/{template_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.edit`

**Request Body:** Same fields as Create (all optional).

**Response:** `200 OK` — Updated `TemplateRead`.

---

### 8.5 Delete Template

```
DELETE /templates/{template_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.delete`

**Response:** `204 No Content`

---

### 8.6 List Template Elements

```
GET /templates/{template_id}/elements
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.view`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "template_id": "uuid",
    "element_type": "text",
    "label": "اسم الضيف",
    "data_key": "guest.full_name_ar",
    "x": 100, "y": 500, "width": 880, "height": 80,
    "rotation": 0,
    "font_family": "Cairo",
    "font_size": 48,
    "font_weight": "bold",
    "font_color": "#ffffff",
    "text_align": "center",
    "text_direction": "rtl",
    "line_height": 1.4,
    "letter_spacing": 0,
    "is_visible": true,
    "z_index": 10,
    "sort_order": 1
  }
]
```

> **Frontend Note:** Elements are positioned on a canvas of `width_px × height_px`. Use `x`, `y`, `width`, `height` for absolute positioning. `data_key` maps to invitation data (see Data Keys section below).

**Available `element_type` values:**
| Type | Description |
|------|-------------|
| `text` | Dynamic text (from data_key) |
| `static_text` | Fixed text |
| `qr_code` | QR barcode |
| `image` | Static image |
| `shape` | Rectangle/circle/line |
| `barcode` | 1D barcode |
| `divider` | Horizontal line |
| `icon` | Icon element |
| `logo` | Logo image |
| `stamp` | Decorative stamp |
| `watermark` | Watermark overlay |
| `background` | Background layer |
| `frame` | Border frame |

**Available `data_key` values (for dynamic text):**
| Key | Example Value |
|-----|---------------|
| `guest.full_name` | Ahmed Al-Ali |
| `guest.full_name_ar` | أحمد العلي |
| `guest.phone` | +966501234567 |
| `guest.email` | ahmed@example.com |
| `guest.company` | شركة التقنية |
| `guest.title` | المدير التنفيذي |
| `guest.custom_fields.seat` | A12 |
| `event.title` | حفل تخرج 2026 |
| `event.title_ar` | حفل تخرج ٢٠٢٦ |
| `event.start_date` | 2026-06-15 |
| `event.venue_name` | فندق الريتز |
| `event.venue_name_ar` | فندق الريتز |
| `invite.code` | INV-001 |
| `invite.token` | a1b2c3... |
| `invite.ticket_class` | vip |
| `custom.seat` | A12 |
| `custom.table` | 5 |
| `custom.gate` | البوابة الرئيسية |
| `custom.hall` | القاعة الكبرى |
| `custom.zone` | VIP |

---

### 8.7 Add Element

```
POST /templates/{template_id}/elements
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.edit`

**Request Body:**
```json
{
  "element_type": "text",
  "label": "اسم الضيف",
  "data_key": "guest.full_name_ar",
  "x": 100, "y": 500, "width": 880, "height": 80,
  "rotation": 0,
  "font_family": "Cairo",
  "font_size": 48,
  "font_weight": "bold",
  "font_color": "#ffffff",
  "text_align": "center",
  "text_direction": "rtl",
  "line_height": 1.4,
  "letter_spacing": 0,
  "qr_size": null,
  "qr_color": null,
  "qr_bg_color": null,
  "qr_error_level": null,
  "static_content": null,
  "is_visible": true,
  "z_index": 10,
  "sort_order": 1
}
```

**Response:** `201 Created` — `ElementRead`.

---

### 8.8 Update Element

```
PATCH /templates/{template_id}/elements/{element_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.edit`

**Request Body:** Same fields as Add (all optional).

**Response:** `200 OK` — Updated `ElementRead`.

---

### 8.9 Delete Element

```
DELETE /templates/{template_id}/elements/{element_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.edit`

**Response:** `204 No Content`

---

### 8.10 Replace All Elements (Canvas Save)

```
PUT /templates/{template_id}/elements
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.edit`
**Replaces ALL elements** of a template in one call. Used by the canvas editor "Save" button.

**Request Body:** Array of `ElementCreate` objects.

**Response:** `200 OK` — Array of created `ElementRead`.

> **Frontend Note:** On canvas save, serialize all elements and send them in a single PUT. This is atomic — old elements are deleted and new ones are created.

---

### 8.11 Upload Background

```
POST /templates/{template_id}/background
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.edit`
Upload via `multipart/form-data`.

**Form Data:**
| Field | Type | Description |
|-------|------|-------------|
| `file` | File | PNG, JPEG, or WebP. Max 10MB. |

**Response:** `200 OK`
```json
{
  "background_url": "https://signed-url...",
  "file_size": 2456789
}
```

---

### 8.12 Upload Asset (Overlay/Font/Logo)

```
POST /templates/{template_id}/assets?asset_type=font
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.edit`
Upload via `multipart/form-data`.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `asset_type` | string | `overlay`, `logo`, `stamp`, `font` |

**Form Data:**
| Field | Type | Description |
|-------|------|-------------|
| `file` | File | Image or font file |

**Font restrictions:**
- **Allowed formats:** `.ttf`, `.otf` only (WOFF/WOFF2 not supported)
- **Max size:** 5MB
- **Validation:** Magic byte check (TTF/OTF signatures)

**Response:** `200 OK` — `AssetRead`.

---

### 8.13 List Assets

```
GET /templates/{template_id}/assets
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.view`

**Response:** `200 OK` — Array of `AssetRead`.

---

### 8.14 Delete Asset

```
DELETE /templates/{template_id}/assets/{asset_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `templates.edit`

**Response:** `204 No Content`

---

## 9. Guests

### 9.1 List Guests

```
GET /guests?search=أحمد
```

🔒 **Auth required.** 🛡️ **Permission:** `guests.view`

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Search by name, phone, or email (ILIKE) |

**Response:** `200 OK` — Array of `GuestRead` (max 200).

---

### 9.2 Create Guest

```
POST /guests
```

🔒 **Auth required.** 🛡️ **Permission:** `guests.create`

**Request Body:**
```json
{
  "full_name": "Ahmed Al-Ali",                  // required
  "full_name_ar": "أحمد العلي",                  // optional
  "phone": "+966501234567",                      // optional
  "email": "ahmed@example.com",                  // optional
  "company": "شركة التقنية",                     // optional
  "title": "المدير التنفيذي",                    // optional
  "notes": "...",                                // optional
  "tags": ["vip", "speaker"],                    // optional
  "custom_fields": { "department": "IT" },       // optional
  "metadata": {}                                 // optional
}
```

**Response:** `201 Created` — `GuestRead`.

---

### 9.3 Get Guest

```
GET /guests/{guest_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `guests.view`

**Response:** `200 OK` — `GuestRead`.

---

### 9.4 Update Guest

```
PATCH /guests/{guest_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `guests.edit`

**Request Body:** Same fields as Create (all optional).

**Response:** `200 OK` — Updated `GuestRead`.

---

### 9.5 Delete Guest

```
DELETE /guests/{guest_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `guests.delete`

**Response:** `204 No Content`

---

### 9.6 Bulk Import Guests

```
POST /guests/import
```

🔒 **Auth required.** 🛡️ **Permission:** `guests.import`

**Request Body:**
```json
{
  "guests": [
    {
      "full_name": "أحمد العلي",
      "full_name_ar": "أحمد العلي",
      "phone": "+966501234567",
      "email": "ahmed@example.com",
      "company": "شركة التقنية",
      "title": "مدير",
      "notes": "",
      "tags": ["vip"],
      "custom_fields": {}
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "imported": 150
}
```

> **Frontend Note:** For CSV/Excel import, parse the file client-side and convert to the JSON format above.

---

## 10. Generation Batches

### 10.1 List Batches

```
GET /batches?event_id=uuid&status=ready&limit=50
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.view`

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | Filter by event |
| `status` | string | `draft`, `queued`, `processing`, `ready`, `failed`, `cancelled` |
| `limit` | int | Max 200, default 50 |

**Response:** `200 OK` — Array of `BatchSummary`.

---

### 10.2 Get Batch

```
GET /batches/{batch_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.view`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "event_id": "uuid",
  "template_id": "uuid",
  "mode": "designed",
  "ticket_class": "vip",
  "status": "processing",
  "progress": 65,
  "count_total": 100,
  "count_done": 65,
  "count_failed": 2,
  "layout_json": { ... },
  "output_formats": ["pdf", "zip"],
  "barcode_format": "qr",
  "result_pdf_url": null,
  "result_zip_url": null,
  "result_preview_urls": [],
  "error_message": null,
  "started_at": "2026-02-10T14:00:00",
  "completed_at": null,
  "created_by": "uuid",
  "created_at": "2026-02-10T13:55:00",
  "updated_at": "2026-02-10T14:05:00"
}
```

> **Frontend Note:** Poll `GET /batches/{id}` every 2–3 seconds while `status` is `queued` or `processing`. Use `progress` (0–100) for a progress bar.

---

### 10.3 Get Batch Items

```
GET /batches/{batch_id}/items?status=failed&limit=100
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.view`

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `status` | string | `pending`, `done`, `failed`, `skipped` |
| `limit` | int | Max 1000, default 100 |

**Response:** `200 OK` — Array of `BatchItemRead` (per-invitation status).

---

### 10.4 Create Batch

```
POST /batches
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.create`

**Request Body:**
```json
{
  "event_id": "uuid",                           // required
  "template_id": "uuid",                        // required for "designed" mode
  "mode": "designed",                            // "quick" | "designed"
  "ticket_class": "vip",                        // "vip" | "normal"
  "output_formats": ["pdf", "zip"],             // optional
  "barcode_format": "qr",                       // optional
  "invitation_ids": ["uuid1", "uuid2"],         // optional — if null, uses all for event+class
  "layout": {                                    // required
    "page_size": "A4",                           // "A4" | "Letter" | "custom"
    "orientation": "portrait",                   // "portrait" | "landscape"
    "margin_mm": 10,
    "gap_mm": 5,
    "dpi": 300,
    "barcode_size_px": null                      // null = auto-calculate
  },
  "metadata": {}                                 // optional
}
```

**Response:** `201 Created` — `BatchRead` with `status: "draft"`.

---

### 10.5 Start Batch

```
POST /batches/{batch_id}/start
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.create`
Triggers the generation pipeline (Celery worker). Transitions `draft`/`failed` → `queued`.

**Response:** `200 OK`
```json
{
  "message": "تم بدء التوليد",
  "batch_id": "uuid",
  "status": "queued"
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `400` | لا يمكن بدء دفعة بحالة: processing |

> **Frontend Note:** After calling start, begin polling `GET /batches/{id}` for progress updates.

---

### 10.6 Cancel Batch

```
POST /batches/{batch_id}/cancel
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.manage`

**Response:** `200 OK`
```json
{
  "message": "تم إلغاء الدفعة"
}
```

---

### 10.7 Retry Failed Batch

```
POST /batches/{batch_id}/retry
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.manage`
Only re-processes **failed items** (idempotent — already-done items are skipped).

**Response:** `200 OK`
```json
{
  "message": "تم إعادة المحاولة",
  "batch_id": "uuid"
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `400` | يمكن إعادة المحاولة فقط للدفعات الفاشلة |

---

### 10.8 Download PDF

```
GET /batches/{batch_id}/download/pdf
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.view`
Returns a fresh **signed URL** (expires in 1 hour).

**Response:** `200 OK`
```json
{
  "url": "https://signed-url-to-pdf...",
  "expires_in": 3600
}
```

> **Frontend Note:** Open this URL in a new tab or trigger a download. The URL expires in 1 hour.

---

### 10.9 Download ZIP

```
GET /batches/{batch_id}/download/zip
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.view`

**Response:** Same format as PDF download.

---

### 10.10 Batch Stats

```
GET /batches/{batch_id}/stats
```

🔒 **Auth required.** 🛡️ **Permission:** `batches.view`

**Response:** `200 OK`
```json
{
  "batch": {
    "id": "uuid",
    "status": "ready",
    "progress": 100,
    "mode": "designed",
    "started_at": "2026-02-10T14:00:00",
    "completed_at": "2026-02-10T14:12:00"
  },
  "items": {
    "total": 100,
    "done": 98,
    "failed": 2,
    "pending": 0,
    "skipped": 0
  },
  "failed_details": [
    {
      "id": "uuid",
      "invitation_id": "uuid",
      "error_message": "Font not found: CustomFont.ttf",
      "guest_name": "أحمد العلي"
    }
  ],
  "result": {
    "pdf_url": "https://...",
    "zip_url": "https://...",
    "preview_urls": ["https://preview_0.png", "https://preview_1.png"]
  }
}
```

---

## 11. Roles & Permissions

### 11.1 List System Permissions

```
GET /roles/permissions
```

🔒 **Auth required.** 🛡️ **Permission:** `roles.view`

**Response:** `200 OK`
```json
[
  { "key": "events.create", "description": "Create events" },
  { "key": "events.view", "description": "View events" },
  { "key": "events.edit", "description": "Edit events" },
  { "key": "events.delete", "description": "Delete events" },
  { "key": "events.publish", "description": "Publish events" },
  { "key": "invitations.create", "description": "Create invitations" },
  { "key": "invitations.view", "description": "View invitations" },
  { "key": "invitations.revoke", "description": "Revoke invitations" },
  { "key": "invitations.send", "description": "Send invitations" },
  { "key": "checkin.scan", "description": "Scan QR codes" },
  { "key": "checkin.manual", "description": "Manual check-in" },
  { "key": "checkin.view", "description": "View check-in history" },
  { "key": "templates.create", "description": "Create templates" },
  { "key": "templates.view", "description": "View templates" },
  { "key": "templates.edit", "description": "Edit templates" },
  { "key": "templates.delete", "description": "Delete templates" },
  { "key": "guests.create", "description": "Create guests" },
  { "key": "guests.view", "description": "View guests" },
  { "key": "guests.edit", "description": "Edit guests" },
  { "key": "guests.delete", "description": "Delete guests" },
  { "key": "guests.import", "description": "Import guests" },
  { "key": "batches.create", "description": "Create batches" },
  { "key": "batches.view", "description": "View batches" },
  { "key": "batches.manage", "description": "Manage batches" },
  { "key": "roles.view", "description": "View roles" },
  { "key": "roles.manage", "description": "Manage roles" },
  { "key": "members.view", "description": "View members" },
  { "key": "members.manage", "description": "Manage members" },
  { "key": "settings.view", "description": "View settings" },
  { "key": "settings.manage", "description": "Manage settings" },
  { "key": "teams.view", "description": "View teams" },
  { "key": "teams.manage", "description": "Manage teams" },
  { "key": "gates.view", "description": "View gates" },
  { "key": "gates.manage", "description": "Manage gates" },
  { "key": "features.manage", "description": "Manage feature flags" }
]
```

> **Frontend Note:** Use this list to build a permission picker UI when creating/editing custom roles.

---

### 11.2 List Roles

```
GET /roles
```

🔒 **Auth required.** 🛡️ **Permission:** `roles.view`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "name": "Admin",
    "description": "Full access",
    "is_system_role": true,
    "created_at": "2026-01-01T00:00:00",
    "permissions": ["events.create", "events.view", "...all 62..."]
  }
]
```

**Default system roles:**
| Role | Permissions |
|------|-------------|
| **Admin** | All 62 permissions |
| **Member** | events.*, invitations.*, guests.*, batches.create/view, templates.view |
| **Designer** | templates.*, files.*, view-only for events/invitations |
| **Check-in Staff** | checkin.scan, checkin.manual, checkin.view, events.view |
| **Viewer** | *.view only + batches.view |

---

### 11.3 Get Role

```
GET /roles/{role_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `roles.view`

**Response:** `200 OK` — `RoleRead` with permissions array.

---

### 11.4 Create Custom Role

```
POST /roles
```

🔒 **Auth required.** 🛡️ **Permission:** `roles.manage`

**Request Body:**
```json
{
  "name": "Event Manager",
  "description": "Can manage events and invitations",
  "permissions": ["events.create", "events.view", "events.edit", "invitations.create", "invitations.view"]
}
```

**Response:** `201 Created` — `RoleRead`.

**Errors:**
| Code | Detail |
|------|--------|
| `409` | يوجد دور بنفس الاسم |
| `400` | صلاحيات غير موجودة: xyz.abc |

---

### 11.5 Update Role

```
PATCH /roles/{role_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `roles.manage`
System roles cannot be modified.

**Request Body (all optional):**
```json
{
  "name": "Senior Event Manager",
  "description": "Updated description",
  "permissions": ["events.create", "events.view", "events.edit", "events.delete"]
}
```

**Response:** `200 OK` — Updated `RoleRead`.

---

### 11.6 Delete Role

```
DELETE /roles/{role_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `roles.manage`
System roles cannot be deleted. Roles assigned to members cannot be deleted.

**Response:** `204 No Content`

**Errors:**
| Code | Detail |
|------|--------|
| `403` | لا يمكن حذف الأدوار النظامية |
| `409` | لا يمكن حذف دور مُسند لأعضاء |

---

### 11.7 Assign Role to Member

```
POST /roles/assign?member_id=uuid&role_id=uuid
```

🔒 **Auth required.** 🛡️ **Permission:** `members.manage`

**Response:** `200 OK`
```json
{
  "message": "تم إسناد الدور بنجاح"
}
```

---

### 11.8 Unassign Role from Member

```
POST /roles/unassign?member_id=uuid&role_id=uuid
```

🔒 **Auth required.** 🛡️ **Permission:** `members.manage`

**Response:** `200 OK`
```json
{
  "message": "تم إزالة الدور بنجاح"
}
```

---

## 12. Team Invites

> These are **team member invitations** (invite someone to join your organization), not event invitations.

### 12.1 Send Team Invite

```
POST /invites
```

🔒 **Auth required.** 🛡️ **Permission:** Admin role.
Sends an email invitation to join the tenant.

**Request Body:**
```json
{
  "email": "newmember@example.com",
  "role": "member"                               // "owner" | "admin" | "member" | "viewer"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "email": "newmember@example.com",
  "role": "member",
  "status": "pending",
  "invited_by": "uuid",
  "token": "invite-token...",
  "expires_at": "2026-02-17T14:00:00",
  "accepted_at": null,
  "created_at": "2026-02-10T14:00:00"
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `409` | User is already a member |
| `409` | Invite already pending for this email |
| `429` | Seats limit reached (N). Upgrade your plan. |

---

### 12.2 List Team Invites

```
GET /invites
```

🔒 **Auth required.** 🛡️ **Permission:** Admin role.

**Response:** `200 OK` — Array of `InviteRead`.

---

### 12.3 Accept Team Invite

```
POST /invites/accept/{token}
```

🔒 **Auth required.** The authenticated user's email must match the invite email.

**Response:** `200 OK`
```json
{
  "message": "تم قبول الدعوة بنجاح",
  "tenant_id": "uuid",
  "role": "member"
}
```

**Errors:**
| Code | Detail |
|------|--------|
| `400` | Invite has expired |
| `403` | This invite was sent to a different email address |
| `409` | You are already a member of this tenant |

---

### 12.4 Revoke Team Invite

```
DELETE /invites/{invite_id}
```

🔒 **Auth required.** 🛡️ **Permission:** Admin role.

**Response:** `204 No Content`

---

## 13. Teams

### 13.1 List Teams

```
GET /teams
```

🔒 **Auth required.** 🛡️ **Permission:** `teams.view`

**Response:** `200 OK` — Array of `TeamRead`.

---

### 13.2 Create Team

```
POST /teams
```

🔒 **Auth required.** 🛡️ **Permission:** `teams.manage`

**Request Body:**
```json
{
  "name": "فريق التصميم",
  "description": "مسؤول عن تصميم البطاقات",
  "color": "#e91e63"
}
```

**Response:** `201 Created` — `TeamRead`.

---

### 13.3 Get Team

```
GET /teams/{team_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `teams.view`

**Response:** `200 OK` — `TeamRead`.

---

### 13.4 Update Team

```
PATCH /teams/{team_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `teams.manage`

**Request Body (all optional):**
```json
{
  "name": "فريق التصميم المتقدم",
  "description": "...",
  "color": "#2196f3"
}
```

**Response:** `200 OK` — Updated `TeamRead`.

---

### 13.5 Delete Team

```
DELETE /teams/{team_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `teams.manage`

**Response:** `204 No Content`

---

### 13.6 List Team Members

```
GET /teams/{team_id}/members
```

🔒 **Auth required.** 🛡️ **Permission:** `teams.view`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "team_id": "uuid",
    "user_id": "uuid",
    "role": "lead",
    "joined_at": "2026-02-01T00:00:00",
    "full_name": "أحمد العلي",
    "avatar_url": "https://..."
  }
]
```

---

### 13.7 Add Team Member

```
POST /teams/{team_id}/members
```

🔒 **Auth required.** 🛡️ **Permission:** `teams.manage`

**Request Body:**
```json
{
  "user_id": "uuid",
  "role": "member"                               // "lead" | "member"
}
```

**Response:** `201 Created` — `TeamMemberRead`.

---

### 13.8 Remove Team Member

```
DELETE /teams/{team_id}/members/{user_id}
```

🔒 **Auth required.** 🛡️ **Permission:** `teams.manage`

**Response:** `204 No Content`

---

## 14. Subscriptions & Plans

### 14.1 List Plans (Public)

```
GET /plans
```

🌐 **No auth required.**

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "code": "free",
    "name": "Free",
    "price_monthly": 0,
    "price_yearly": 0,
    "currency": "USD",
    "is_active": true,
    "sort_order": 1,
    "limits": [
      { "id": "uuid", "plan_id": "uuid", "key": "events_max", "value": 3, "period": "month" },
      { "id": "uuid", "plan_id": "uuid", "key": "invitations_max", "value": 100, "period": "month" },
      { "id": "uuid", "plan_id": "uuid", "key": "seats_max", "value": 2, "period": null },
      { "id": "uuid", "plan_id": "uuid", "key": "storage_mb", "value": 100, "period": null }
    ]
  },
  {
    "code": "pro",
    "name": "Pro",
    "price_monthly": 29,
    "limits": [ ... ]
  }
]
```

> **Frontend Note:** Use this for the pricing page. Show plan comparison table with limits.

---

### 14.2 Get Current Subscription

```
GET /subscriptions/current
```

🔒 **Auth required.** 🛡️ **Permission:** Admin role.

**Response:** `200 OK` — `SubscriptionWithPlan`.

---

### 14.3 Create Checkout Session

```
POST /subscriptions/checkout?plan_code=pro
```

🔒 **Auth required.** 🛡️ **Permission:** Admin role.
Creates a Stripe Checkout session for upgrading.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `plan_code` | string | `pro`, `enterprise`, etc. |

**Response:** `200 OK`
```json
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_..."
}
```

> **Frontend Note:** Redirect the user to `checkout_url`. After payment, Stripe redirects to `/billing/success?session_id=...`.

---

### 14.4 Cancel Subscription

```
POST /subscriptions/cancel
```

🔒 **Auth required.** 🛡️ **Permission:** Owner only.
Cancels at period end (not immediately).

**Response:** `200 OK`
```json
{
  "message": "Subscription will be canceled at period end"
}
```

---

## 15. Usage & Limits

### 15.1 Get Usage and Limits

```
GET /usage
```

🔒 **Auth required.** (Membership check only)

**Response:** `200 OK`
```json
{
  "plan_code": "pro",
  "limits": [
    { "key": "events_max", "limit": 50, "used": 12, "remaining": 38, "exceeded": false },
    { "key": "invitations_max", "limit": 5000, "used": 1234, "remaining": 3766, "exceeded": false },
    { "key": "seats_max", "limit": 10, "used": 5, "remaining": 5, "exceeded": false },
    { "key": "storage_mb", "limit": 500, "used": 123, "remaining": 377, "exceeded": false }
  ]
}
```

> **Frontend Note:** Show usage bars in the billing/settings page. Warn when approaching limits.

---

## 16. Audit Logs

### 16.1 List Audit Logs

```
GET /audit-logs?action=event.create&resource_type=event&limit=50&offset=0
```

🔒 **Auth required.** 🛡️ **Permission:** Admin role.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `action` | string | Filter: `event.create`, `invitation.revoke`, `member.join`, etc. |
| `resource_type` | string | Filter: `event`, `invitation`, `template`, `batch`, etc. |
| `limit` | int | Max 200, default 50 |
| `offset` | int | Pagination offset |

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "actor_user_id": "uuid",
    "action": "event.create",
    "resource_type": "event",
    "resource_id": "uuid",
    "metadata": { "title": "حفل تخرج" },
    "ip_address": "192.168.1.1",
    "user_agent": null,
    "created_at": "2026-02-10T14:00:00"
  }
]
```

---

## 17. Platform Admin

> 🛡️ **Staff only** — requires `is_staff = true` in the user's profile.

### 17.1 List All Tenants

```
GET /platform/tenants?status=active&plan=pro&search=شركة&limit=50&offset=0
```

**Response:** `200 OK` — Array of `PlatformTenantRead` (includes `members_count`).

---

### 17.2 Get Tenant Detail

```
GET /platform/tenants/{tenant_id}
```

**Response:** `200 OK` — `PlatformTenantRead`.

---

### 17.3 Suspend Tenant

```
POST /platform/tenants/{tenant_id}/suspend
```

**Response:** `200 OK`
```json
{ "message": "تم تعليق المستأجر بنجاح" }
```

---

### 17.4 Activate Tenant

```
POST /platform/tenants/{tenant_id}/activate
```

Re-activates a suspended or cancelled tenant.

**Response:** `200 OK`
```json
{ "message": "تم تفعيل المستأجر بنجاح" }
```

---

### 17.5 Cancel Tenant

```
POST /platform/tenants/{tenant_id}/cancel
```

Permanently cancels a tenant.

**Response:** `200 OK`
```json
{ "message": "تم إلغاء المستأجر" }
```

---

### 17.6 Platform Stats

```
GET /platform/stats
```

**Response:** `200 OK`
```json
{
  "total_tenants": 150,
  "active_tenants": 120,
  "trial_tenants": 20,
  "suspended_tenants": 5,
  "total_users": 500,
  "total_memberships": 600,
  "active_subscriptions": 140
}
```

---

## 18. Webhooks

### 18.1 Stripe Webhook

```
POST /webhooks/stripe
```

🌐 **No auth required** (verified via Stripe signature).
Not included in API schema. Handles:

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Activate subscription |
| `invoice.paid` | Extend subscription period |
| `invoice.payment_failed` | Mark as past_due |
| `customer.subscription.deleted` | Cancel + downgrade to free |

> **Idempotent:** Stores `stripe_event_id` with UNIQUE constraint. Duplicate events are acknowledged (200) without reprocessing.

---

## 19. Enums & Constants

### Invitation Status Flow

```
created → sent → viewed → accepted/declined → checked_in
                                              → revoked (any time)
                                              → expired (auto)
```

| Status | Description |
|--------|-------------|
| `created` | Just created, not sent yet |
| `sent` | Delivered to guest |
| `viewed` | Guest opened the invitation link |
| `accepted` | Guest accepted via RSVP |
| `declined` | Guest declined via RSVP |
| `checked_in` | Guest checked in at the event |
| `revoked` | Manually cancelled by admin |
| `expired` | Auto-expired after event end |

### Batch Status Flow

```
draft → queued → processing → ready
                            → failed → (retry) → queued
       → cancelled (any time before ready)
```

| Status | Description |
|--------|-------------|
| `draft` | Created, not started |
| `queued` | Waiting for worker |
| `processing` | Worker is generating |
| `ready` | Complete — PDF/ZIP available |
| `failed` | Error occurred (can retry) |
| `cancelled` | Manually cancelled |

### Ticket Classes

| Value | Description |
|-------|-------------|
| `vip` | VIP guest |
| `normal` | Regular guest |

### Check-in Results

| Value | Description |
|-------|-------------|
| `success` | Successfully checked in |
| `already_checked_in` | Was already checked in |
| `revoked` | Invitation was revoked |
| `expired` | Invitation expired |
| `wrong_event` | Token belongs to different event |
| `wrong_gate` | Ticket class not allowed at this gate |
| `invalid` | Token not found |

### Template Types

| Value | Description |
|-------|-------------|
| `quick` | Simple barcode grid (no design) |
| `designed` | Full card design with elements |

### Tenant Status

| Value | Description |
|-------|-------------|
| `trial` | Free trial period |
| `active` | Active subscription |
| `suspended` | Suspended by admin |
| `cancelled` | Permanently cancelled |

---

## 20. Error Codes

All errors follow this format:

```json
{
  "detail": "رسالة الخطأ بالعربية"
}
```

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `400` | Bad Request | Missing required field, invalid value, business rule violation |
| `401` | Unauthorized | Missing/expired JWT token |
| `403` | Forbidden | No permission for this action |
| `404` | Not Found | Resource doesn't exist or belongs to another tenant |
| `409` | Conflict | Duplicate entry (email, slug, domain) |
| `410` | Gone | Invitation revoked or expired |
| `429` | Too Many Requests | Rate limit exceeded. Check `Retry-After` header. |

> **Frontend Note:** Error messages are in Arabic. Display `detail` directly to the user.

---

## Quick Reference: Frontend Pages → API Mapping

| Page | Primary Endpoints |
|------|-------------------|
| **Login** | `POST /auth/login`, `GET /auth/me` |
| **Dashboard** | `GET /events`, `GET /usage` |
| **Event Detail** | `GET /events/{id}`, `GET /events/{id}/stats` |
| **Invitations List** | `GET /invitations?event_id=...` |
| **Create Invitation** | `POST /invitations` or `POST /invitations/quick` |
| **Guest Directory** | `GET /guests`, `POST /guests`, `POST /guests/import` |
| **Template Editor** | `GET /templates/{id}/elements`, `PUT /templates/{id}/elements` |
| **Batch Generation** | `POST /batches`, `POST /batches/{id}/start`, poll `GET /batches/{id}` |
| **Check-in Scanner** | `POST /checkin/scan`, `GET /checkin/live/{event_id}` |
| **Public Invitation** | `GET /invitations/view/{token}`, `POST /invitations/rsvp/{token}` |
| **Billing** | `GET /plans`, `GET /subscriptions/current`, `POST /subscriptions/checkout` |
| **Settings** | `GET /tenants/current/settings`, `GET /tenants/current/members` |
| **Roles Management** | `GET /roles`, `GET /roles/permissions`, `POST /roles` |
| **Audit Log** | `GET /audit-logs` |
| **Platform Admin** | `GET /platform/tenants`, `GET /platform/stats` |

---

> **Document generated from source code — 120 endpoints across 14 route files.**
> For architecture details, see `SYSTEM_ARCHITECTURE.md`.
