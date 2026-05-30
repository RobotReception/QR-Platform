# 📱 Darai Mobile App — API Documentation
### وثيقة تقنية شاملة لمطور تطبيق الموبايل

> **الإصدار**: 1.0  
> **التاريخ**: 2026-04-09  
> **Base URL**: `https://devdarai.prideidea.com/api/backend/v2`

---

## 📌 الإعداد العام

### Headers المطلوبة في كل طلب:
```http
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
Content-Type: application/json
Accept-Language: ar
```

> `Accept-Language` يقبل `ar` أو `en` — يُرجع الأسماء والتسميات بالعربية أو الإنجليزية

### بنية الاستجابة الموحدة:
```jsonc
// ✅ نجاح
{
  "success": true,
  "message": "تمت العملية بنجاح",
  "data": { /* البيانات */ }
}

// ❌ خطأ
{
  "success": false,
  "message": "وصف الخطأ",
  "data": null
}
```

### أكواد الحالة:
| Code | المعنى |
|------|--------|
| `200` | نجاح |
| `201` | تم الإنشاء |
| `400` | خطأ في البيانات المرسلة |
| `401` | غير مصرح (توكن منتهي أو غير صالح) |
| `403` | ممنوع (لا توجد صلاحية) |
| `404` | غير موجود |
| `409` | تعارض (مكرر) |
| `422` | خطأ في التحقق |
| `429` | تجاوز حد الطلبات |
| `500` | خطأ سيرفر |

---

# ═══════════════════════════════════════════════════════
# 1. 🔐 المصادقة (تسجيل الدخول + كلمة المرور فقط)
# ═══════════════════════════════════════════════════════

## 1.1 `POST /auth/login` — تسجيل الدخول

> لا يحتاج Authorization header

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response** `200`:
```json
{
  "success": true,
  "message": "تم تسجيل الدخول بنجاح",
  "data": {
    "user": {
      "id": "3912d0ba-2a23-4861-8152-8a039faa6706",
      "email": "user@example.com",
      "username": "user@example.com",
      "tenant_id": "alrazi",
      "role": "owner",
      "first_name": "Mohammed",
      "last_name": "alshebly",
      "phone": "+967775451608",
      "profile_picture": null,
      "email_verified": true,
      "onboarding_complete": true,
      "pageWithPermission": {
        "totalPages": 1072347627,
        "permissions": [
          { "pageValue": 1, "totalValue": 31 },
          { "pageValue": 2, "totalValue": 66978694 },
          { "pageValue": 8, "totalValue": 1 },
          { "pageValue": 32, "totalValue": 6206 },
          { "pageValue": 64, "totalValue": 63 },
          { "pageValue": 128, "totalValue": 4160749568 },
          { "pageValue": 256, "totalValue": 1205862400 }
        ]
      }
    },
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 900
  }
}
```

> **ملاحظات مهمة**:
> - `expires_in`: مدة صلاحية الـ access_token بالثواني (900 = 15 دقيقة)
> - `profile_picture`: قد يكون `null` إذا لم يتم تعيين صورة
> - `pageWithPermission`: نظام صلاحيات Bitmask:
>   - `totalPages`: قيمة OR لكل الصفحات المتاحة
>   - `permissions[].pageValue`: رقم الصفحة (Bitmask)
>   - `permissions[].totalValue`: صلاحيات الصفحة (Bitmask)
>   - يُستخدم كـ opaque data — يُخزَّن ويُرسل كما هو
> - `role`: يمكن أن يكون `owner` | `admin` | `agent` | `supervisor`
```

> ⚠️ **حالة خاصة — اختيار المنظمة**: إذا الإيميل مسجل في أكثر من منظمة:
```json
{
  "success": true,
  "data": {
    "requires_tenant_selection": true,
    "email": "user@example.com",
    "tenants": [
      { "tenant_id": "tenant_001", "organization_name": "شركة الرازي", "role": "admin" },
      { "tenant_id": "tenant_002", "organization_name": "مؤسسة النور", "role": "agent" }
    ]
  }
}
```
> → أعد طلب Login مع إضافة Header: `X-Tenant-Id: tenant_001`

---

## 1.2 `POST /auth/refresh-token` — تجديد التوكن

> لا يحتاج Authorization

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOi_NEW_ACCESS...",
    "refresh_token": "eyJhbGciOi_NEW_REFRESH...",
    "expires_in": 86400
  }
}
```

---

## 1.3 `POST /auth/logout` — تسجيل الخروج

**Response** `200`:
```json
{ "success": true, "message": "Logged out successfully", "data": {} }
```

---

## 1.4 `POST /auth/password/reset/request` — طلب إعادة كلمة المرور

> لا يحتاج Authorization

**Request**:
```json
{ "email": "user@example.com" }
```

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "message": "OTP sent to email",
    "email": "user@example.com",
    "expires_in": 300,
    "otp_length": 6,
    "max_attempts": 3,
    "attempts_remaining": 3,
    "cooldown_in": 60
  }
}
```

---

## 1.5 `POST /auth/password/reset/confirm` — تأكيد إعادة التعيين بالـ OTP

> لا يحتاج Authorization

**Request**:
```json
{
  "email": "user@example.com",
  "otp": "123456",
  "new_password": "NewSecurePass123!"
}
```

**Response** `200`:
```json
{
  "success": true,
  "data": { "message": "Password reset successfully", "email": "user@example.com" }
}
```

---

## 1.6 `POST /auth/password/update` — تغيير كلمة المرور (مسجل دخول)

**Request**:
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```

---

## 1.7 `GET /auth/saas/tenants/current` — بيانات المنظمة

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "tenant_id": "tenant_xyz789",
    "name": "شركة الرازي",
    "domain": "razi",
    "logo": "https://media.darai.com/logos/razi.png",
    "industry": "education",
    "country": "YE",
    "timezone": "Asia/Aden",
    "language": "ar"
  }
}
```

---

### آلية التجديد التلقائي للتوكن:
```
 طلب عادي → السيرفر رجّع 401؟
    ├── نعم → POST /auth/refresh-token
    │         ├── نجح → كرر الطلب الأصلي بالتوكن الجديد
    │         └── فشل → ارجع لشاشة Login
    └── لا → استمر
```

---

# ═══════════════════════════════════════════════════════
# 2. 💬 المحادثات (Inbox + Customers)
# ═══════════════════════════════════════════════════════

> جميع الـ endpoints تتطلب `Authorization` header
> endpoints الـ `/customers/*` تتطلب `?account_id=acc_xxx` كـ query parameter

---

## 2.1 `GET /inbox/sidebar-summary` — ملخص الـ Inbox

**Query Params**: `?user_id=xxx` (اختياري، تلقائي من التوكن)

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "all": 156,
    "mine": 23,
    "unassigned": 45,
    "by_lifecycle": [
      { "code": "lead", "name": "عميل محتمل", "count": 80 },
      { "code": "customer", "name": "عميل", "count": 50 },
      { "code": "vip", "name": "VIP", "count": 26 }
    ],
    "by_team": [
      { "team_id": "team_01", "name": "فريق المبيعات", "count": 40 },
      { "team_id": "team_02", "name": "الدعم الفني", "count": 35 }
    ]
  }
}
```

---

## 2.2 `GET /inbox/customers` — قائمة المحادثات

**جميع Query Params**:
| Param | النوع | مطلوب | الوصف |
|-------|-------|-------|-------|
| `page` | `int` | لا | رقم الصفحة (default: 1) |
| `limit` | `int` | لا | عدد لكل صفحة (default: 20) |
| `search` | `string` | لا | بحث بالاسم أو الرقم |
| `platform` | `string` | لا | `whatsapp` \| `facebook` \| `instagram` \| `webchat` \| `telegram` |
| `lifecycle` | `string` | لا | كود دورة الحياة |
| `assigned_to` | `string` | لا | UUID الموظف أو `me` |
| `session_status` | `string` | لا | `open` \| `closed` |
| `account_id` | `string` | لا | معرف الحساب/القناة |
| `team_id` | `string` | لا | معرف الفريق |
| `is_assigned` | `bool` | لا | هل معيّن لموظف |
| `is_assigned_team` | `bool` | لا | هل معيّن لفريق |
| `enable_ai_q` | `bool` | لا | حالة AI |
| `unread_only` | `bool` | لا | الغير مقروءة فقط |
| `favorite` | `bool` | لا | المفضلة فقط |
| `muted` | `bool` | لا | المكتومة فقط |
| `start_date` | `string` | لا | من تاريخ `2024-01-01` |
| `end_date` | `string` | لا | إلى تاريخ |
| `sort_by` | `string` | لا | حقل الترتيب (default: `last_message_at`) |
| `sort_order` | `string` | لا | `desc` \| `asc` |
| `include_filters` | `bool` | لا | إرجاع خيارات الفلاتر |

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "customer_id": "967775451608",
        "name": "أحمد محمد",
        "phone": "+967775451608",
        "platform": "whatsapp",
        "account_id": "acc_whatsapp_01",
        "session_id": "sess_abc123",
        "session_status": "pending",
        "is_open": true,
        "lifecycle": { "code": "customer", "name": "عميل", "color": "#22c55e" },
        "assigned_to": { "user_id": "usr_xxx", "name": "سارة", "profile_picture": "https://..." },
        "assigned_team": { "team_id": "team_01", "name": "المبيعات" },
        "enable_ai": true,
        "is_favorite": false,
        "is_muted": false,
        "unread_count": 3,
        "last_message": {
          "text": "مرحباً، أريد الاستفسار",
          "type": "text",
          "direction": "incoming",
          "timestamp": "2024-03-15T14:30:00Z"
        },
        "tags": [{ "tag_id": "tag_01", "name": "عاجل", "emoji": "🔴" }],
        "created_at": "2024-01-10T08:00:00Z"
      }
    ],
    "total": 156,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "has_next": true,
    "has_previous": false
  }
}
```

---

## 2.3 `GET /customers/accounts` — قائمة حسابات القنوات

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "accounts": [
      { "account_id": "acc_whatsapp_01", "platform": "whatsapp", "name": "واتساب الرسمي", "phone_number": "+967777000111" },
      { "account_id": "acc_instagram_01", "platform": "instagram", "name": "انستقرام", "ig_account_id": "17841234567890" }
    ]
  }
}
```

---

## 2.4 `GET /customers/{customer_id}/basic-info` — معلومات العميل

**Query**: `?account_id=acc_xxx` **(مطلوب)**

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "customer_id": "967775451608",
    "name": "أحمد محمد",
    "phone": "+967775451608",
    "email": "ahmed@example.com",
    "platform": "whatsapp",
    "profile_picture": "https://...",
    "lifecycle": { "code": "customer", "name": "عميل" },
    "assigned_to": { "user_id": "usr_xxx", "name": "سارة" },
    "teams": [{ "team_id": "team_01", "name": "المبيعات" }],
    "tags": [{ "tag_id": "tag_vip", "name": "VIP", "emoji": "⭐" }],
    "enable_ai": true,
    "is_favorite": false,
    "is_muted": false,
    "session_status": "pending",
    "is_open": true,
    "unread_count": 3,
    "custom_fields": {
      "first_name": "أحمد",
      "last_name": "محمد",
      "city": "صنعاء",
      "company": "شركة النور"
    },
    "created_at": "2024-01-10T08:00:00Z",
    "last_seen_at": "2024-03-15T14:30:00Z"
  }
}
```

---

## 2.5 `GET /customers/{customer_id}/messages` — رسائل المحادثة

**Query Params**:
| Param | النوع | مطلوب | الوصف |
|-------|-------|-------|-------|
| `account_id` | `string` | ✅ | معرف الحساب |
| `page` | `int` | لا | رقم الصفحة (default: 1) |
| `page_size` | `int` | لا | عدد الرسائل (default: 50, max: 200) |
| `before_timestamp` | `string` | لا | cursor لرسائل أقدم |

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "message_id": "msg_001",
        "type": "text",
        "direction": "incoming",
        "content": { "text": "مرحباً" },
        "sender": { "id": "967775451608", "name": "أحمد", "type": "customer" },
        "timestamp": "2024-03-15T14:30:00Z",
        "status": "read"
      },
      {
        "message_id": "msg_002",
        "type": "image",
        "direction": "incoming",
        "content": { "url": "https://media.darai.com/img_xxx.jpg", "caption": "صورة المنتج" },
        "sender": { "id": "967775451608", "name": "أحمد", "type": "customer" },
        "timestamp": "2024-03-15T14:32:00Z"
      },
      {
        "message_id": "msg_003",
        "type": "text",
        "direction": "outgoing",
        "content": { "text": "أهلاً! كيف يمكنني مساعدتك؟" },
        "sender": { "id": "admin:sara@company.com", "name": "سارة", "type": "agent", "profile_picture": "https://..." },
        "timestamp": "2024-03-15T14:33:00Z",
        "status": "delivered"
      },
      {
        "message_id": "act_001",
        "type": "activity",
        "direction": "system",
        "content": { "text": "سارة أغلقت المحادثة", "action": "close_conversation" },
        "timestamp": "2024-03-15T15:00:00Z"
      },
      {
        "message_id": "cmt_001",
        "type": "comment",
        "direction": "internal",
        "content": { "text": "يرجى المتابعة @محمد", "mentions": ["usr_mohammed"] },
        "sender": { "id": "admin:sara@company.com", "name": "سارة", "type": "agent" },
        "timestamp": "2024-03-15T15:05:00Z"
      }
    ],
    "pagination": { "page": 1, "page_size": 50, "total": 120, "has_next": true, "has_previous": false }
  }
}
```

> **أنواع الرسائل**: `text` | `image` | `video` | `audio` | `document` | `interactive` | `comment` (داخلي) | `activity` (نظامي)
> **الاتجاه**: `incoming` (من العميل) | `outgoing` (من الموظف) | `system` | `internal`
> **حالة الإرسال**: `sent` | `delivered` | `read` | `failed`

---

## 2.6 `POST /inbox/send-message` — إرسال رسالة

**Request**:
```json
{
  "platform": "whatsapp",
  "recipient_id": "967775451608",
  "sender_id": "admin:user@company.com",
  "responder": "admin:user@company.com",
  "message_type": "text",
  "content": { "text": "مرحباً بك!" },
  "sender_info": {
    "name": "سارة أحمد",
    "profile_picture": "https://media.darai.com/avatars/sara.jpg"
  },
  "account_id": "acc_whatsapp_01",
  "original_msg_id": null,
  "response_to": null
}
```

**`content` حسب `message_type`**:
| message_type | content |
|-------------|---------|
| `text` | `{ "text": "مرحباً" }` |
| `image` | `{ "url": "https://...", "caption": "وصف" }` |
| `video` | `{ "url": "https://...", "caption": "وصف" }` |
| `audio` | `{ "url": "https://..." }` |
| `document` | `{ "url": "https://...", "filename": "ملف.pdf", "caption": "وصف" }` |

> الـ `url` للوسائط يتم الحصول عليه بعد رفع الملف عبر `POST /media/upload`

**Response** `200`:
```json
{
  "success": true,
  "message": "Message sent successfully",
  "data": { "message_id": "msg_new_001", "status": "sent", "timestamp": "2024-03-15T14:35:00Z" }
}
```

---

## 2.7 `POST /inbox/comments` — تعليق داخلي

> لا يظهر للعميل — يدعم @mentions

**Request**:
```json
{
  "customer_id": "967775451608",
  "session_id": "sess_abc123",
  "platform": "whatsapp",
  "sender_id": "admin:user@company.com",
  "sender_type": "agent",
  "sender_info": { "name": "سارة أحمد", "profile_picture": "https://..." },
  "content": {
    "text": "يرجى المتابعة @محمد",
    "mentions": ["usr_mohammed_id"]
  }
}
```

---

## 2.8 `GET /customers/{customer_id}/ai-check` — فحص حالة AI

**Query**: `?account_id=acc_xxx`

**Response**: `{ "data": { "customer_id": "...", "enable_ai": true, "ai_active": true } }`

---

## 2.9 `PATCH /customers/{customer_id}/enable-ai` — تفعيل/تعطيل AI

**Query**: `?account_id=acc_xxx`

```json
{
  "enable_ai": false,
  "reason": "العميل يحتاج دعم بشري",
  "team_id": "team_support_01"
}
```

---

## 2.10 `PATCH /customers/{customer_id}/assign` — تعيين موظف

**Query**: `?account_id=acc_xxx`

```jsonc
// تعيين:
{ "assigned_to": "usr_sara_uuid", "assigned_to_username": "سارة أحمد", "is_assigned": true, "performed_by_name": "المدير" }

// إلغاء التعيين:
{ "assigned_to": null, "is_assigned": false }
```

---

## 2.11 `PATCH /customers/{customer_id}/session-status` — تغيير حالة الجلسة

**Query**: `?account_id=acc_xxx`

```json
{ "session_status": "pending" }
```

> القيم: `pending` (مفتوحة) | `resolved` | `closed`

---

## 2.12 `PATCH /customers/{customer_id}/close-conversation` — إغلاق المحادثة

**Query**: `?account_id=acc_xxx`

```json
{ "reason": "تم حل المشكلة", "category": "resolved", "lang": "ar" }
```

---

## 2.13 `PATCH /customers/{customer_id}/reopen-conversation` — إعادة فتح

**Query**: `?account_id=acc_xxx`

```json
{ "user_id": "usr_to_reassign_uuid" }
```

---

## 2.14 `PATCH /customers/{customer_id}/lifecycle` — تغيير دورة الحياة

**Query**: `?account_id=acc_xxx`

```json
{ "lifecycle_code": "vip" }
```

---

## 2.15 `GET /customers/{customer_id}/teams` — فرق العميل

**Query**: `?account_id=acc_xxx`

**Response**: `{ "data": { "teams": [{ "team_id": "team_01", "name": "المبيعات" }] } }`

---

## 2.16 `PUT /customers/{customer_id}/teams` — تعيين فرق

**Query**: `?account_id=acc_xxx`

```json
{ "teams": ["team_01", "team_02"], "is_assigned_team": true }
```

---

## 2.17 `DELETE /customers/{customer_id}/teams` — إزالة فرق

**Query**: `?account_id=acc_xxx`

```json
{ "teams": ["team_01"] }
```

---

## 2.18 `POST /customers/{customer_id}/tags` — إضافة علامات

**Query**: `?account_id=acc_xxx`

```json
{ "tags": ["tag_urgent", "tag_vip"] }
```

---

## 2.19 `DELETE /customers/{customer_id}/tags` — إزالة علامات

**Query**: `?account_id=acc_xxx`

```json
{ "tags": ["tag_urgent"] }
```

---

## 2.20 `PATCH /customers/{customer_id}/favorite` — إضافة/إزالة المفضلة

**Query**: `?account_id=acc_xxx`

```json
{ "favorite": true }
```

---

## 2.21 `PATCH /customers/{customer_id}/mute` — كتم/إلغاء كتم

**Query**: `?account_id=acc_xxx`

```json
{ "muted": true }
```

---

## 2.22 `PATCH /customers/{customer_id}/mark-read` — تعليم كمقروء

**Query**: `?account_id=acc_xxx`  
**Body**: لا يوجد (فقط PATCH بدون body)

---

## 2.W WebSocket — الرسائل الحية 🔴

**الاتصال**:
```
wss://devdarai.prideidea.com/api/backend/v2/ws?token=<access_token>
```

**طرق المصادقة** (بالأولوية):
1. Cookie `fateen_access_token` (تلقائي من الويب)
2. رسالة `auth:<token>` خلال 10 ثوان من الاتصال
3. Query param `?token=<token>`

**الأوامر التي يمكن إرسالها**:
| الأمر | الوصف |
|-------|-------|
| `ping` | يرد بـ `pong` |
| `refresh` | يرسل العداد فوراً |
| `mark_read:<notification_id>` | يحدد مقروء + يحدّث العداد |

**الرسائل المستقبلة**:
```json
{ "type": "count", "user_id": "usr_xxx", "unread": 3, "total": 10 }
```

> يرسل تلقائياً كل 30 ثانية + فوراً عند الاتصال

---

## 2.M `POST /media/upload` — رفع ملف (للإرسال في المحادثة)

```
Content-Type: multipart/form-data

file:       <binary>       (مطلوب)
platform:   "whatsapp"     (مطلوب)
owner_type: "user"         (مطلوب)
source:     "user_upload"  (مطلوب)
```

**Response** `200`:
```json
{ "success": true, "data": { "media_id": "media_abc123", "url": "https://media.darai.com/file.jpg", "content_type": "image/jpeg", "size": 245678 } }
```

## `GET /media/{media_id}/public-url` — رابط الوسائط

**Response**: `{ "data": { "url": "https://cdn.darai.com/file_xxx.jpg" } }`

---

# ═══════════════════════════════════════════════════════
# 3. 🔔 الإشعارات (Notifications) — كامل
# ═══════════════════════════════════════════════════════

## 3.1 `GET /notifications` — قائمة الإشعارات

**Query Params**:
| Param | النوع | الوصف |
|-------|-------|-------|
| `limit` | `int` | عدد النتائج (default: 20, max: 100) |
| `offset` | `int` | بداية الصفحة (default: 0) |

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "notifications": [
      {
        "id": "notif_abc123",
        "user_id": "usr_xxx",
        "title": "رسالة جديدة",
        "body": "أحمد: مرحباً، أريد الاستفسار عن...",
        "data": {
          "type": "message",
          "customer_id": "967775451608",
          "platform": "whatsapp"
        },
        "is_read": false,
        "created_at": "2024-03-15T14:30:00Z"
      },
      {
        "id": "notif_def456",
        "user_id": "usr_xxx",
        "title": "تعيين جديد",
        "body": "تم تعيين العميل سارة لك",
        "data": {
          "type": "assignment",
          "customer_id": "967771234567"
        },
        "is_read": true,
        "created_at": "2024-03-15T13:00:00Z"
      }
    ],
    "total": 45,
    "limit": 20,
    "offset": 0
  }
}
```

> **أنواع الإشعارات** (`data.type`): `message` | `order_created` | `announcement` | `payment` | `reminder` | `security_alert` | `assignment` | `test`

---

## 3.2 `GET /notifications/count` — عداد الإشعارات

> مناسب للاستدعاء كل 5-10 ثوان (HTTP polling)

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "user_id": "usr_xxx",
    "total": 45,
    "unread": 3
  }
}
```

---

## 3.3 `POST /notifications/{notification_id}/mark-read` — تحديد مقروء

**Body**: لا يوجد  
**Response**: `{ "success": true, "message": "تمت العملية بنجاح" }`

---

## 3.4 `POST /notifications/mark-all-read` — تحديد الكل مقروء

**Body**: لا يوجد

**Response** `200`:
```json
{ "success": true, "data": { "updated_count": 4, "user_id": "usr_xxx" } }
```

---

## 3.5 `POST /notifications/register-device` — تسجيل جهاز Push (FCM)

> يُستدعى بعد الحصول على FCM Token من Firebase

**Request**:
```json
{
  "device_token": "fcm_device_token_from_firebase...",
  "device_type": "android",
  "device_name": "Samsung Galaxy S24"
}
```

> **device_type**: `android` | `ios` | `web`

**Response** `200`:
```json
{ "success": true, "data": { "registered": true, "device_type": "android" } }
```

---

## 3.6 `GET /notifications/my-devices` — أجهزتي المسجلة

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "devices": [
      { "device_token": "fcm_xxx...", "device_type": "android", "device_name": "Samsung Galaxy S24", "registered_at": "2024-03-01T10:00:00Z" },
      { "device_token": "fcm_yyy...", "device_type": "ios", "device_name": "iPhone 15 Pro", "registered_at": "2024-02-15T08:00:00Z" }
    ]
  }
}
```

---

## 3.7 `POST /notifications/send` — إرسال إشعار (Admin)

**Request**:
```json
{
  "user_id": "usr_target_uuid",
  "title": "تذكير مهم",
  "body": "لديك 3 محادثات بانتظار الرد",
  "data": { "type": "reminder" }
}
```

---

## 3.W WebSocket — عداد الإشعارات Real-time

> نفس WebSocket المذكور في قسم المحادثات (2.W)
> يرسل تلقائياً `{ "type": "count", "unread": N }` كل 30 ثانية

---

# ═══════════════════════════════════════════════════════
# 4. 👥 جهات الاتصال (Contacts) — كامل
# ═══════════════════════════════════════════════════════

## 4.1 `GET /contacts/contacts` — قائمة جهات الاتصال

**جميع Query Params**:
| Param | النوع | الوصف |
|-------|-------|-------|
| `skip` | `int` | عدد العناصر للتخطي (default: 0) |
| `limit` | `int` | عدد لكل صفحة (default: 20, max: 100) |
| `search` | `string` | بحث في: الاسم، customer_id، الملاحظات |
| `platform` | `string` | `whatsapp` \| `webchat` \| `facebook` \| `instagram` \| `telegram` |
| `session_status` | `string` | `pending` \| `open` \| `closed` |
| `assigned_to` | `string` | UUID الموظف المعيّن |
| `lifecycle` | `string` | كود دورة الحياة |
| `tags` | `string` | علامات (فاصلة): `vip,urgent` |
| `enable_ai` | `bool` | حالة AI |
| `conversation_status` | `string` | `open` \| `closed` |
| `team_id` | `string` | معرف الفريق (فاصلة لأكثر من واحد) |
| `is_assigned_team` | `string` | `true` \| `false` |
| `sort_by` | `string` | حقل الترتيب (default: `updated_at`) |
| `sort_order` | `string` | `desc` \| `asc` |
| `account_id` | `string` | معرف الحساب |

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "contacts": [
      {
        "customer_id": "967775451608",
        "sender_name": "أحمد محمد",
        "platform": "whatsapp",
        "platform_icon": "https://...",
        "is_contacts": true,
        "session_status": "pending",
        "lifecycle": "customer",
        "enable_ai": true,
        "tags": [{ "tag_id": "tag_vip", "name": "VIP" }],
        "team_ids": { "teams": [{ "team_id": "team_01", "name": "المبيعات" }] },
        "assigned": { "assigned_to": "usr_xxx", "is_assigned": true },
        "custom_fields": {
          "first_name": "أحمد",
          "last_name": "محمد",
          "phone": "+967775451608",
          "email": "ahmed@example.com",
          "city": "صنعاء",
          "company": "شركة النور"
        },
        "notes": "عميل مهم، يتابع طلب خاص",
        "conversation_status": { "is_closed": false },
        "last_message": "مرحباً",
        "last_direction": "incoming",
        "unread_count": 2,
        "created_at": "2024-01-10T08:00:00Z",
        "updated_at": "2024-03-15T14:30:00Z"
      }
    ],
    "pagination": {
      "totalCount": 250,
      "totalPages": 13,
      "currentPage": 1,
      "pageSize": 20,
      "hasPrevious": false,
      "hasNext": true
    }
  }
}
```

---

## 4.2 `POST /contacts/contacts` — إنشاء جهة اتصال

**Query**: `?account_id=acc_xxx` (اختياري)

**Request**:
```json
{
  "customer_id": "967775451608",
  "additional_fields": {
    "first_name": "أحمد",
    "last_name": "محمد",
    "email": "ahmed@example.com",
    "city": "صنعاء"
  },
  "notes": "عميل جديد من واتساب"
}
```

---

## 4.3 `GET /contacts/contacts/{customer_id}` — تفاصيل جهة اتصال

**Query**: `?account_id=acc_xxx` (اختياري)

**Response**: نفس بنية العنصر في القائمة (4.1)

---

## 4.4 `PUT /contacts/contacts/{customer_id}` — تحديث جهة اتصال

> Partial Update — فقط الحقول المرسلة تتغير
> `custom_fields` → يتم **دمجها** مع القيم الحالية
> `tags` → يتم **استبدالها** بالكامل

**Query**: `?account_id=acc_xxx` (اختياري)

**Request** (أرسل الحقول المطلوب تحديثها فقط):
```json
{
  "sender_name": "أحمد الرازي",
  "custom_fields": {
    "city": "عدن",
    "company": "شركة الابتكار"
  },
  "notes": "تم تحديث البيانات",
  "lifecycle": "vip",
  "tags": ["tag_vip", "tag_premium"],
  "enable_ai": false
}
```

**جميع الحقول القابلة للتحديث**:

| الحقل | النوع | الوصف |
|-------|-------|-------|
| `sender_name` | `string` | اسم العرض |
| `platform` | `string` | المنصة |
| `custom_fields` | `object` | حقول مخصصة (دمج) |
| `contact_fields` | `object` | حقول أساسية |
| `notes` | `string` | ملاحظات (max: 1000) |
| `assigned` | `object` | `{ "assigned_to": "uuid", "is_assigned": true }` |
| `session_status` | `string` | حالة الجلسة |
| `lifecycle` | `string` | دورة الحياة |
| `tags` | `list[string]` | العلامات (استبدال كامل) |
| `enable_ai` | `bool` | تفعيل AI |
| `conversation_status` | `object` | `{ "is_closed": true, "close_reason": "..." }` |
| `last_message` | `string` | آخر رسالة |
| `last_direction` | `string` | `incoming` \| `outgoing` |

---

## 4.5 `DELETE /contacts/contacts/{customer_id}` — حذف (Soft Delete)

**Query**: `?account_id=acc_xxx` (اختياري)

> يحذف من قائمة جهات الاتصال فقط (is_contacts=false) — لا يحذف العميل

---

## 4.6 `PUT /contacts/contacts/{customer_id}/custom-fields` — تحديث الحقول المخصصة فقط

**Query**: `?account_id=acc_xxx` (اختياري)

```json
{
  "custom_fields": {
    "city": "عدن",
    "language": "ar"
  }
}
```

---

## 4.7 `POST /contacts/contacts/{customer_id}/convert` — تحويل

```json
{ "is_contact": true }
```

> `true` لإعادة جهة اتصال محذوفة، `false` لإزالتها

---

## 4.8 `GET /contacts/contacts/stats/summary` — إحصائيات

**Query**: `?account_id=acc_xxx` (اختياري)

---

## 4.9 `GET /contacts/contacts/sidebar-summary` — ملخص جانبي

**Query**: `?user_id=xxx&account_id=acc_xxx`

---

## 4.10 `GET /contacts/contacts/filters` — خيارات الفلترة

**Query**: `?account_id=acc_xxx`

> يرجع القيم الفريدة لكل فلتر (platform, lifecycle, tags, ...) مع العدد

---

## 4.11 `GET /contacts/contacts/fields/required` — الحقول المطلوبة

> يرجع قائمة الحقول المطلوبة والاختيارية (لبناء الفورم)

---

## 4.12 `GET /contacts/contacts/search/customers` — بحث عملاء للتحويل

**Query**: `?search=أحمد&limit=10`

> يبحث في العملاء الذين يمكن تحويلهم لجهات اتصال

---

## 4.13 `GET /contacts/contacts/export` — تصدير Excel/CSV

**Query**: نفس فلاتر القائمة (4.1)

> يرجع ملف `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

---

## 4.14 `POST /contacts/contacts/bulk/convert` — تحويل مجموعة

```json
{ "customer_ids": ["967775451608", "967771234567"], "requested_by": "admin@company.com" }
```

---

## 4.15 `POST /contacts/contacts/bulk/fields` — تحديث حقول مجموعة

```json
{
  "updates": [
    { "customer_id": "967775451608", "additional_fields": { "city": "عدن" } },
    { "customer_id": "967771234567", "additional_fields": { "city": "صنعاء" } }
  ]
}
```

---

### الحقول الديناميكية (Dynamic Fields)

## 4.D1 `GET /contacts/contacts/dynamic-fields` — قائمة الحقول المخصصة

**Query**: `?field_type=text` (اختياري)

**Response**:
```json
{
  "success": true,
  "data": {
    "fields": [
      {
        "field_name": "company",
        "field_label": "الشركة",
        "label_ar": "الشركة",
        "label_en": "Company",
        "field_type": "text",
        "required": false,
        "default_value": null,
        "options": null,
        "is_active": true,
        "display_order": 1
      },
      {
        "field_name": "priority",
        "field_label": "الأولوية",
        "field_type": "select",
        "required": true,
        "options": ["عالية", "متوسطة", "منخفضة"],
        "is_active": true,
        "display_order": 2
      }
    ]
  }
}
```

> **أنواع الحقول** (`field_type`): `text` | `number` | `email` | `phone` | `date` | `boolean` | `select` | `multi_select` | `url` | `textarea`

---

## 4.D2 `POST /contacts/contacts/dynamic-fields` — إنشاء حقل

```json
{
  "field_name": "company",
  "field_label": "الشركة",
  "label_ar": "الشركة",
  "label_en": "Company",
  "field_type": "text",
  "required": false,
  "default_value": null,
  "is_active": true,
  "display_order": 5,
  "description": "اسم شركة العميل"
}
```

> لحقول `select` / `multi_select` أضف: `"options": ["خيار 1", "خيار 2"]`

---

## 4.D3 `GET /contacts/contacts/dynamic-fields/{field_name}` — تفاصيل حقل
## 4.D4 `PUT /contacts/contacts/dynamic-fields/{field_name}` — تحديث حقل (partial)
## 4.D5 `DELETE /contacts/contacts/dynamic-fields/{field_name}` — حذف حقل (نهائي)

---

# ═══════════════════════════════════════════════════════
# 5. 👤 البروفايل
# ═══════════════════════════════════════════════════════

## 5.1 `GET /user/profile`

**Response** `200`:
```json
{
  "success": true,
  "data": {
    "user_id": "usr_a1b2c3d4",
    "email": "user@company.com",
    "name": "أحمد محمد",
    "first_name": "أحمد",
    "last_name": "محمد",
    "phone": "+966512345678",
    "role": "admin",
    "profile_picture": "https://media.darai.com/avatars/ahmed.jpg",
    "is_active": true,
    "tenant_id": "tenant_xyz789",
    "language": "ar",
    "timezone": "Asia/Aden",
    "email_verified": true,
    "onboarding_complete": true,
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-03-10T12:00:00Z"
  }
}
```

---

## 5.2 `PATCH /user/profile` — تحديث البروفايل

```json
{
  "first_name": "أحمد",
  "last_name": "الرازي",
  "phone": "+966512345678",
  "language": "ar",
  "timezone": "Asia/Aden"
}
```

---

# ═══════════════════════════════════════════════════════
# 📊 ملخص Endpoints حسب الشاشة
# ═══════════════════════════════════════════════════════

### 🔑 تسجيل الدخول (7 endpoints)
| Endpoint | العملية |
|----------|---------|
| `POST /auth/login` | دخول |
| `POST /auth/refresh-token` | تجديد توكن |
| `POST /auth/logout` | خروج |
| `POST /auth/password/reset/request` | طلب OTP |
| `POST /auth/password/reset/confirm` | تأكيد بـ OTP |
| `POST /auth/password/update` | تغيير كلمة المرور |
| `GET /auth/saas/tenants/current` | بيانات المنظمة |

### 💬 المحادثات (22 endpoint + WebSocket + Media)
| Endpoint | العملية |
|----------|---------|
| `GET /inbox/sidebar-summary` | ملخص |
| `GET /inbox/customers` | قائمة المحادثات |
| `GET /customers/accounts` | حسابات القنوات |
| `GET /customers/{id}/basic-info` | معلومات العميل |
| `GET /customers/{id}/messages` | الرسائل |
| `POST /inbox/send-message` | إرسال |
| `POST /inbox/comments` | تعليق داخلي |
| `GET /customers/{id}/ai-check` | فحص AI |
| `PATCH /customers/{id}/enable-ai` | تفعيل/تعطيل AI |
| `PATCH /customers/{id}/assign` | تعيين موظف |
| `PATCH /customers/{id}/session-status` | تغيير الحالة |
| `PATCH /customers/{id}/close-conversation` | إغلاق |
| `PATCH /customers/{id}/reopen-conversation` | إعادة فتح |
| `PATCH /customers/{id}/lifecycle` | دورة الحياة |
| `GET /customers/{id}/teams` | فرق العميل |
| `PUT /customers/{id}/teams` | تعيين فرق |
| `DELETE /customers/{id}/teams` | إزالة فرق |
| `POST /customers/{id}/tags` | إضافة علامات |
| `DELETE /customers/{id}/tags` | إزالة علامات |
| `PATCH /customers/{id}/favorite` | مفضلة |
| `PATCH /customers/{id}/mute` | كتم |
| `PATCH /customers/{id}/mark-read` | تعليم مقروء |
| `POST /media/upload` | رفع وسائط |
| `GET /media/{id}/public-url` | رابط الملف |
| `WSS /ws` | أحداث حية |

### 🔔 الإشعارات (7 endpoints + WebSocket)
| Endpoint | العملية |
|----------|---------|
| `GET /notifications` | القائمة |
| `GET /notifications/count` | العداد |
| `POST /notifications/{id}/mark-read` | تحديد مقروء |
| `POST /notifications/mark-all-read` | الكل مقروء |
| `POST /notifications/register-device` | تسجيل FCM |
| `GET /notifications/my-devices` | أجهزتي |
| `POST /notifications/send` | إرسال إشعار |
| `WSS /ws` | عداد حي |

### 👥 جهات الاتصال (20 endpoint)
| Endpoint | العملية |
|----------|---------|
| `GET /contacts/contacts` | القائمة |
| `POST /contacts/contacts` | إنشاء |
| `GET /contacts/contacts/{id}` | التفاصيل |
| `PUT /contacts/contacts/{id}` | تحديث |
| `DELETE /contacts/contacts/{id}` | حذف |
| `PUT /contacts/contacts/{id}/custom-fields` | حقول مخصصة |
| `POST /contacts/contacts/{id}/convert` | تحويل |
| `GET /contacts/contacts/stats/summary` | إحصائيات |
| `GET /contacts/contacts/sidebar-summary` | ملخص |
| `GET /contacts/contacts/filters` | فلاتر |
| `GET /contacts/contacts/fields/required` | حقول مطلوبة |
| `GET /contacts/contacts/search/customers` | بحث |
| `GET /contacts/contacts/export` | تصدير |
| `POST /contacts/contacts/bulk/convert` | تحويل مجموعة |
| `POST /contacts/contacts/bulk/fields` | تحديث مجموعة |
| `GET /contacts/contacts/dynamic-fields` | الحقول الديناميكية |
| `POST /contacts/contacts/dynamic-fields` | إنشاء حقل |
| `GET /contacts/contacts/dynamic-fields/{name}` | تفاصيل حقل |
| `PUT /contacts/contacts/dynamic-fields/{name}` | تحديث حقل |
| `DELETE /contacts/contacts/dynamic-fields/{name}` | حذف حقل |

### 👤 البروفايل (2 endpoints)
| Endpoint | العملية |
|----------|---------|
| `GET /user/profile` | جلب البروفايل |
| `PATCH /user/profile` | تحديث البروفايل |

---

> **المجموع الكلي: 58 endpoint + 1 WebSocket**
