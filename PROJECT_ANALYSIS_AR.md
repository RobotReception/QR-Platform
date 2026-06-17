# تحليل مشروع QR / Qentry — منصة الدعوات الرقمية

> تحليل تقني شامل للمشروع الموجود في `D:\QR`
> تاريخ التحليل: 2026-06-17

---

## 1. نظرة عامة (ما هو المشروع؟)

**Qentry** هي منصة SaaS متعددة المستأجرين (Multi-tenant) لإدارة **المناسبات والدعوات الرقمية مع رموز QR**.
الفكرة: شركة/منظّم فعاليات ينشئ حدثاً، يستورد قائمة الضيوف، يصمّم بطاقة دعوة، يولّد آلاف الدعوات بـ QR موقّعة، يرسلها، ثم يسجّل دخول الضيوف على البوابات عبر مسح QR.

**اللغة الأساسية للواجهة:** العربية (RTL) مع دعم إنجليزي.

### المكوّنات الرئيسية
| المكوّن | التقنية | الموقع |
|---------|---------|--------|
| Backend API | FastAPI (Python 3) | `app/` (~17.6k سطر، 63 ملف) |
| Frontend | React 18 + TypeScript + Vite | `frontend/src/` (~26k سطر، 102 ملف) |
| قاعدة البيانات | PostgreSQL عبر Supabase | `supabase/` (27 ملف SQL) |
| المعالجة الخلفية | Celery + Redis | `app/worker.py` |
| موقع تسويقي | HTML/CSS ثابت | `landing/` |
| التخزين | Supabase Storage | bucket `invitations` |

---

## 2. معمارية الـ Backend (FastAPI)

### نمط تعدد المستأجرين (Multi-tenancy)
- **نموذج مشترك (Shared DB / Shared Schema)**: كل الجداول تحوي عمود `tenant_id`، والعزل منطقي عبر `WHERE tenant_id = ...`.
- **حلّ المستأجر** عبر `TenantResolutionMiddleware` (`app/middleware.py`) بثلاث استراتيجيات بالترتيب:
  1. هيدر `X-Tenant-ID` أو `X-Tenant-Slug`
  2. النطاق الفرعي (subdomain)
  3. النطاق المخصّص (custom domain) من جدول `tenant_domains`
- المستأجر يُخزّن في `contextvars` طوال عمر الطلب (`app/tenant_context.py`)، فيمكن لأي كود استدعاء `get_current_tenant_id()` دون تمريره.
- يتم فرض حالة المستأجر (active/trial فقط؛ suspended/cancelled/deleted تُحجب).

### طبقة الوصول لقاعدة البيانات
- **مزدوجة**:
  - **SQLAlchemy Async + asyncpg** للعمليات المباشرة (`app/database.py`)، مع `NullPool` و `statement_cache_size=0` (توافقاً مع PgBouncer).
  - **عميل Supabase** (service-role للعمليات الإدارية + anon).
- ملاحظة مهمة: **النماذج في `app/models/` هي Pydantic schemas فقط** — لا توجد ORM models فعلية. كل استعلامات DB مكتوبة بـ **SQL خام** عبر `text(...)`.
- **حارس العزل** `TenantQuery` (`app/services/tenant_query.py`): مُغلِّف يفرض `tenant_id` في كل SELECT/UPDATE/DELETE/INSERT. الاستثناء الوحيد: نقاط token العامة (view/rsvp).

### المصادقة (Auth)
- مبنية على **Supabase Auth** بـ JWT (`app/auth.py`).
- يدعم `HS256` (عبر `supabase_jwt_secret`) و `ES256/RS256` (عبر JWKS مع تخزين مؤقت).
- `get_current_user` يفكّ التوكن لاستخراج `sub` (user_id) والبريد والدور.

### الصلاحيات (RBAC)
- نظام صلاحيات دقيق عبر دوال PostgreSQL: `user_has_permission`, `get_user_permissions`.
- `permission_service.py` المركز، مع `require_permission` / `require_any_permission`.
- نظام **aliases** (`permission_aliases.py`) يربط مفاتيح الواجهة `ui.*` بمفاتيح الـ API القديمة (legacy) — لتوافق تعيينات الأدوار بين الواجهة والـ backend.
- الأدوار الافتراضية تُنشأ تلقائياً عند تجهيز المستأجر: Admin, Member, Designer, Check-in Staff, Viewer.

### Middleware (بالترتيب)
1. `TenantResolutionMiddleware` — حلّ المستأجر
2. `SecurityHeadersMiddleware` — رؤوس أمان (X-Frame-Options, nosniff, إلخ)
3. `RateLimitMiddleware` — تحديد المعدّل بثلاث طبقات (عام 120/د، نقاط عامة 30/د، check-in 300/د + burst)
4. `CORSMiddleware`

---

## 3. خريطة نقاط النهاية (Routes)

19 راوتر تحت `/api/v1`. أبرزها:

| الراوتر | البادئة | الغرض |
|---------|---------|-------|
| `auth` | `/auth` | تسجيل، دخول، تحديث توكن، استعادة كلمة المرور بـ OTP، تغيير كلمة المرور |
| `tenants` | `/tenants` | إنشاء/إدارة المستأجر، الأعضاء، الإعدادات، النطاقات، feature flags |
| `events` | `/events` | المناسبات، الفئات، الأنواع، البوابات (gates)، الإحصائيات، النشر |
| `digital_invitations` | `/invitations` | إنشاء دعوات (فردي/سريع/جماعي من ضيوف)، إلغاء، إرسال، **view/rsvp عام بالـ token** |
| `fast_invitations` | `/fast-invitations` | توليد سريع مُصمَّم، تنزيل PDF/ZIP، سجل التوليد، الإحصائيات |
| `batches` | `/batches` | دفعات التوليد، البدء/الإلغاء/إعادة المحاولة، التنزيل |
| `checkin` | `/checkin` | **مسح QR**، تسجيل دخول يدوي، السجل، البث المباشر |
| `guests` | `/guests` | إدارة الضيوف + استيراد |
| `templates` | `/templates` | القوالب، العناصر، الخلفيات، الأصول، **معاينة**، خطوط، **توليد بالـ AI** |
| `teams` | `/teams` | الفرق وأعضاؤها (لتعيين البوابات) |
| `registration_forms` | `/events/.../registration-form` + `/public/...` | نماذج التسجيل العامة |
| `subscriptions` | (مختلط) | الخطط، الاشتراك الحالي، checkout، **webhooks (Stripe/PayPal)**, الخطط المخصّصة، الإضافات |
| `platform` | `/platform` | لوحة المشرف العام: تحليلات، إدارة المستأجرين/المستخدمين/الخطط/الأدوار |
| `dashboard`, `usage`, `audit`, `roles`, `profiles`, `invites` | — | تحليلات، حدود الاستخدام، سجل التدقيق، الأدوار، الملف الشخصي، دعوات الأعضاء |

---

## 4. نموذج البيانات (الجداول الرئيسية)

تطوّر عبر **16 migration** (v2 → v16). أهم الجداول:

**النواة (SaaS):** `profiles`, `tenants`, `tenant_domains`, `memberships`, `roles`, `permissions`, `role_permissions`, `membership_roles`, `plans`, `plan_limits`, `subscriptions`, `subscription_events`, `usage_counters`, `invites`, `tenant_settings`, `feature_flags`, `audit_logs`.

**منصة الدعوات (v3+):**
- `events` — المناسبات (عنوان، تاريخ، موقع بإحداثيات، حصص VIP/عادي، RSVP).
- `event_categories`, `event_types`, `event_gates` (بوابات بـ `allowed_classes`), `event_gate_users`.
- `invite_templates` — القوالب (أبعاد، خلفية، quick_style JSONB).
- `template_elements` — عناصر التصميم (إحداثيات نسبية)، `template_assets`.
- `guests` — الضيوف.
- `invitations` — **الدعوة**: `token` فريد (16 بايت hex)، `qr_data`, حصة الضيوف (`guest_count`), مقعد/طاولة/بوابة، حالة RSVP، عدّاد `checkin_count`.
- `invitation_deliveries`, `checkins` — سجلّات الإرسال والدخول.
- `generation_batches`, `batch_items` — دفعات التوليد.
- `registration_forms` — نماذج التسجيل.

**دوال PostgreSQL مهمة:**
- `validate_checkin(token, event_id, gate_id)` — **منطق التحقق من الدخول بالكامل داخل DB** مع `FOR UPDATE` (قفل صفّي يمنع المسح المزدوج). يفحص: وجود الدعوة، تطابق الحدث، الإلغاء، الانتهاء، تجاوز العدد، صلاحية البوابة للفئة، ثم يحدّث الحالة ويزيد العدّاد ذرّياً.
- `increment_usage(tenant, key, amount)` — زيادة عدّاد الاستخدام ذرّياً (`SECURITY DEFINER`).
- `user_has_permission`, `get_user_permissions`, `get_my_tenant_ids`, `is_member_of` — دوال RBAC/RLS.

---

## 5. الخدمات (Services) — قلب المنتج

| الخدمة | الأسطر | الوظيفة |
|--------|-------|---------|
| `render_service.py` | 967 | تركيب صورة الدعوة المصمّمة: خلفية + عناصر بإحداثيات نسبية، نص عربي (reshaping + bidi)، auto-fit، رسم QR في موضعه. **الأضخم والأهم.** |
| `batch_pipeline.py` | 812 | منظّم دورة حياة الدفعة: إنشاء العناصر → توليد barcodes → رندر الصور → رفع. |
| `fast_generation_service.py` | 553 | توليد سريع متكامل: barcode + PDF + ZIP بالتوازي (ThreadPoolExecutor, دفعات 50). |
| `email_service.py` | 496 | إرسال SMTP (دعوات، OTP). |
| `feature_service.py` | 362 | بوّابات الميزات وفحص حدود الخطة. |
| `provisioning_service.py` | 300 | تجهيز المستأجر الجديد (أدوار، إعدادات، feature flags افتراضية). |
| `paypal_service.py` | 278 | اشتراكات ومدفوعات PayPal. |
| `barcode_service.py` | 248 | توليد QR/Code128 (SVG+PNG) مع **توقيع HMAC-SHA256 (128-bit)**. |
| `usage_service.py` | 239 | حدود الخطة والاستخدام (يدعم الخطط المخصّصة). |
| `pdf_service.py` | 217 | توليد PDF (شبكة barcodes أو بطاقات مصمّمة) عبر reportlab. |
| `quota_service.py` | 176 | تحقق مركزي من حصص الدعوات لكل حدث/فئة. |
| `storage_service.py` | 163 | رفع/تنزيل/روابط موقّعة في Supabase Storage. |
| `tenant_query.py` | 188 | حارس فرض `tenant_id` في كل استعلام. |
| أخرى | — | `audit_service`, `membership_service`, `staff_service`, `permission_service`, `permission_aliases`. |

### تدفّق توليد QR والتوقيع
1. `build_barcode_payload(invite_id, token)`: التوقيع = `HMAC_SHA256(key, "invite_id:token").digest()[:16].hex()` (128-bit).
2. الـ QR يُرمّز رابطاً: `{app_url}/i/{token}`.
3. مفتاح HMAC **منفصل** عن JWT secret (`INVITE_HMAC_SECRET`) مع دعم **تدوير المفاتيح** (مفتاح حالي + سابق، نافذة 90 يوماً).

---

## 6. الاشتراكات والفوترة

**5 خطط:** Starter (مجانية) → Basic (200 ر.س/شهر) → Pro (500) → Business (1200) → Enterprise (تسعير مخصص).

**نموذج الحدود** (`plan_limits`, القيمة `-1` = غير محدود): مقاعد، أحداث/شهر، دعوات/حدث، دعوات/شهر، فرق، أعضاء/فريق، قوالب مصمّمة، بوابات/حدث، ضيوف، نماذج تسجيل، تخزين MB، رسائل/شهر، طلبات AI/شهر.

- **خطط مخصّصة** (`custom_plans` v12) + **إضافات (addons)** بتسعير (v14).
- **مزودا دفع:** Stripe و PayPal، مع webhooks لكليهما.
- عدّادات الاستخدام شهرية عبر `increment_usage`.

---

## 7. الـ Frontend (React + TypeScript)

### المكدّس
React 18، Vite 6، TypeScript 5.7، TailwindCSS 3.4، **React Router 6**، **TanStack Query 5** (لجلب البيانات)، **Zustand 5** (الحالة + persist)، **Framer Motion 11** (الأنيميشن)، React Hook Form + Zod، Axios، xlsx (استيراد Excel)، qrcode.

> ملاحظة: ملف `package.json` في الجذر يذكر إصدارات أحدث (React Router 7، Framer Motion 12) لكن frontend يستخدم 6/11 — تعارض إصدارات بين الملفّين.

### البنية
- **تنظيم feature-based**: `src/features/<feature>/{pages,components,hooks,store,api,types,utils,services}`.
- نقطة الدخول `main.tsx` → `QueryClientProvider` → `AppRouter`.
- التوجيه (`src/app/router/index.tsx`): lazy loading، `ProtectedRoute` (يتحقق من المصادقة + hydration)، `StaffRoute` (للمشرف العام).
- مسارات عامة: `/i/:token` (عرض الدعوة)، `/register/:slug` و `/e/:slug` (التسجيل).

### طبقة الخدمات (HTTP)
`src/services/http/client.ts`: Axios مع:
- **Request interceptor**: يرفق `Authorization: Bearer` و `X-Tenant-ID` من localStorage.
- **Response interceptor**: تحديث تلقائي للتوكن عند 401 (refresh)، وإلا مسح التخزين والتوجيه للدخول.

### الميزات حسب الحجم
- **`events` (17.4k سطر — يهيمن على المشروع)**: يحوي محرّر التصميم (`EventDesignEditorPage` 2185 سطر)، أوضاع التصميم/السريع، التابات (barcodes, applicants, RSVP, templates, registration)، استيراد Excel. هذه الميزة تجمع فعلياً الدعوات والضيوف والـ check-in المتداخلة.
- `invitations` (1685): صفحات الدعوة العامة والتسجيل.
- `dashboard` (1634): التحليلات.
- `platform` (1286): لوحة المشرف.
- `auth` (1091)، `teams` (936)، `users` (894)، `settings` (386).
- **مجلدات فارغة** (المنطق منقول داخل `events`): `batches`, `checkin`, `guests`, `landing`, `roles`, `templates`.

### المشترك والتصميم
- `src/shared/`: مكوّنات layout/feedback/navigation، ui، hooks، guards، permissions، types، utils.
- `src/design/`: tokens، themes، fonts، animations (نظام أنيميشن موثّق في `SMOOTH_ANIMATIONS_GUIDE.md`).

---

## 8. التشغيل والنشر

- **محلياً (Windows):** `start.ps1` يشغّل: Docker → Supabase (CLI، DB على 5434) → Backend (uvicorn على **8021**) → Frontend (Vite على **5173**).
- **`docker-compose.yml`:** Postgres 17 (5434) + Redis 7 (6379) فقط — للتطوير.
- **Worker:** `celery -A app.worker worker` (حدود زمنية 30/35 دقيقة، إعادة محاولة، `acks_late`). يمكن التراجع لـ BackgroundTask عبر `USE_WORKER=false`.
- **متغيّرات البيئة** (`.env.example`): Supabase (URL/keys/JWT)، DATABASE_URL، Stripe، PayPal، SMTP، APP_URL، INVITE_HMAC_SECRET، REDIS_URL، STORAGE_BUCKET.

---

## 9. نقاط القوة

1. **عزل المستأجرين منضبط**: حارس `TenantQuery` + middleware + `contextvars` نمط متماسك.
2. **أمان الدعوات جيّد التصميم**: HMAC 128-bit بمفتاح منفصل عن JWT + تدوير مفاتيح + توقيع موثّق بدقّة (تعليق يوضّح لماذا 32 hex وليس 16).
3. **منطق check-in آمن من التزامن**: `validate_checkin` بـ `FOR UPDATE` يمنع المسح المزدوج ذرّياً داخل DB.
4. **تحديد معدّل متدرّج** يراعي طبيعة كل نقطة (نقاط عامة صارمة، check-in عالي الإنتاجية مع burst).
5. **نقاط الـ token العامة محصّنة**: تُرجع حقولاً آمنة فقط، وتحدّث بالـ PK + token معاً (لا تسريب عبر المستأجرين).
6. **معالجة خلفية متينة**: Celery بحدود زمنية وإعادة محاولة و`task_reject_on_worker_lost`.
7. **دعم عربي/RTL حقيقي**: reshaping + bidi في الرندر، رسائل عربية، معالجة ترميز console على Windows.
8. **نموذج فوترة مرن**: خطط ثابتة + مخصّصة + إضافات + مزودا دف��.

## 10. المخاطر ونقاط الضعف (تقنية)

1. **`print()` تشخيصية في الإنتاج**:
   - `app/auth.py:get_tenant_id_from_header` → `print(f"DEBUG: X-Tenant-ID header...")`.
   - `app/middleware.py` → `print(f"TenantResolutionMiddleware: path=...")` على **كل طلب**.
   هذا يسرّب معلومات ويضرّ بالأداء — يجب استبداله بـ logging بمستوى مناسب أو حذفه.
2. **التحقق من الجمهور (audience) معطّل في `get_current_user`** (`options={"verify_aud": False}`). مقبول مع Supabase لكنه يُضعف التحقق؛ يُفضّل التحقق الصريح.
3. **التوقيع (HMAC) لا يُتحقّق منه وقت المسح**: `validate_checkin` يعتمد على الـ token في DB فقط، ولا يُمرّر/يُتحقّق من التوقيع. التوقيع يحمي ضد التزوير دون DB، لكن بما أن التحقق دائماً عبر DB، فقيمة التوقيع العملية محدودة هنا (ليس ثغرة، بل عدم اتساق في النية الأمنية).
4. **تحديد المعدّل في الذاكرة (in-memory)**: لا يصمد مع عدّة عمليات/خوادم؛ التعليق نفسه يوصي بـ Redis للإنتاج.
5. **فوضى ملفات الجذر**: 55 ملف `.md` (توثيق متكرّر/متضارب الإصدارات: 4.2.0 / 4.3.0)، 21 ملف `test_*.py` متناثر، سكربتات migration متعددة (`run_migration_v4*` ×6)، ملفات لقطات PNG ضخمة (debug_template_*.png ~3.5MB، normal_bg.png، supabase.tar/.tar.gz ~130MB داخل المستودع). يجب تنظيفها ونقل الاختبارات إلى `tests/`.
6. **تعارض إصدارات الحزم** بين `package.json` الجذر و `frontend/package.json`.
7. **لا توجد ORM models / Alembic فعّال**: رغم وجود `alembic` في requirements، الهجرات يدوية SQL مرقّمة (v2..v16) مع عدة نسخ schema (`schema.sql`, `schema_complete.sql`, `schema_final.sql`, `schema_simple.sql`) — غموض حول أي ملف هو مصدر الحقيقة.
8. **ميزة "events" متضخّمة (God-feature)**: 17.4k سطر تجمع مسؤوليات متعددة كان يُفترض فصلها (المجلدات الفارغة checkin/guests/templates تدل على نية فصل لم تكتمل).
9. **`.env` فعلي موجود في المجلد** (ليس فقط `.env.example`) — تأكد أنه ضمن `.gitignore` ولم يُرفع.
10. **`@lru_cache` على `get_jwk_for_token(token)`**: يخزّن مؤقتاً حسب التوكن الكامل (وليس kid)، ما يجعل الكاش بلا فائدة فعلية وقد ينمو بلا حدود مع توكنات مختلفة.

---

## 11. خلاصة وتوصيات سريعة

المشروع **منصة SaaS ناضجة وظيفياً** (دعوات + QR + check-in + فوترة + RBAC + تعدد مستأجرين) بمعمارية مدروسة في النواة الأمنية (العزل، HMAC، الأقفال الذرّية). الإصدار الحالي ~4.3.0 موصوف بأنه «جاهز للإنتاج».

**أولويات التحسين:**
1. حذف عبارات `print` التشخيصية واستبدالها بـ logging.
2. نقل تحديد المعدّل إلى Redis.
3. تنظيف الجذر: توحيد التوثيق، نقل الاختبارات لـ `tests/`، إزالة الملفات الثنائية الضخمة من المستودع، تثبيت ملف schema واحد كمصدر حقيقة.
4. حلّ تعارض إصدارات الحزم.
5. تفكيك ميزة `events` المتضخّمة وتفعيل المجلدات الفارغة المقصودة.
6. مراجعة `verify_aud` وكاش JWKS.
