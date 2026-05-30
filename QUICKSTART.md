# ⚡ Quick Start Guide - نظام إدارة القوالب

## 🚀 البدء السريع

### 1️⃣ تشغيل الخدمات (3 نوافذ)

```bash
# Window 1: Backend
cd D:/QR
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Window 2: Frontend  
cd D:/QR/frontend
npm run dev

# Window 3: Database (اختياري - Docker)
docker compose up
```

### 2️⃣ الروابط الأساسية

| الخدمة | الرابط |
|--------|--------|
| 🌐 Frontend | http://localhost:5174 |
| 📚 API Docs | http://127.0.0.1:8000/docs |
| ❤️ Health | http://127.0.0.1:8000/health |

---

## 🔐 الحصول على Token

```bash
python << 'EOF'
from jose import jwt
from datetime import datetime, timedelta

JWT_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"
USER_ID = "b248cc77-fbb9-4b56-a360-d5dcaf5f6938"

payload = {
    "sub": USER_ID,
    "email": "test@example.com",
    "aud": "authenticated",
    "role": "authenticated",
    "iat": int(datetime.utcnow().timestamp()),
    "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp()),
}

print(jwt.encode(payload, JWT_SECRET, algorithm="HS256"))
EOF
```

---

## 📡 أوامر API الأساسية

### جلب جميع القوالب
```bash
curl -H "Authorization: Bearer TOKEN" \
     -H "x-tenant-id: TENANT_ID" \
     http://127.0.0.1:8000/api/v1/templates
```

### إنشاء قالب
```bash
curl -X POST \
     -H "Authorization: Bearer TOKEN" \
     -H "x-tenant-id: TENANT_ID" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "قالب جديد",
       "template_type": "quick",
       "width_px": 1240,
       "height_px": 1754,
       "background_color": "#ffffff"
     }' \
     http://127.0.0.1:8000/api/v1/templates
```

### معاينة القالب
```bash
curl -X POST \
     -H "Authorization: Bearer TOKEN" \
     -H "x-tenant-id: TENANT_ID" \
     -H "Content-Type: application/json" \
     -d '{
       "guest_name": "أحمد علي",
       "event_title": "حفل تخرج",
       "event_date": "2025-06-15",
       "event_time": "19:00",
       "event_location": "فندق الريتز",
       "seat_number": "A12",
       "table_number": "5"
     }' \
     http://127.0.0.1:8000/api/v1/templates/TEMPLATE_ID/preview \
     > preview.png
```

### تحديث القالب
```bash
curl -X PATCH \
     -H "Authorization: Bearer TOKEN" \
     -H "x-tenant-id: TENANT_ID" \
     -H "Content-Type: application/json" \
     -d '{"name":"اسم جديد"}' \
     http://127.0.0.1:8000/api/v1/templates/TEMPLATE_ID
```

### حذف القالب
```bash
curl -X DELETE \
     -H "Authorization: Bearer TOKEN" \
     -H "x-tenant-id: TENANT_ID" \
     http://127.0.0.1:8000/api/v1/templates/TEMPLATE_ID
```

---

## 📂 ملفات مهمة

### Backend
- `app/routes/templates.py` - API routes
- `app/services/render_service.py` - رسم الدعوات
- `app/database.py` - قاعدة البيانات
- `app/auth.py` - نظام المصادقة

### Frontend
- `src/features/events/components/EventTemplatesTab.tsx` - المكون
- `src/features/events/components/EventTemplatesTab.css` - الأنماط
- `frontend/vite.config.ts` - إعدادات Vite

### البيئة
- `.env` - المتغيرات البيئية
- `frontend/.env` - متغيرات Frontend

---

## 🐛 استكشاف الأخطاء

### المشكلة: Backend لا يبدأ
```bash
# تحقق من المنفذ
lsof -i :8000
# أوقف العملية
kill -9 PID
```

### المشكلة: Frontend لا تتصل بـ Backend
```bash
# تأكد من vite.config.ts
# proxy target يجب أن يكون: http://127.0.0.1:8000
curl http://localhost:5174/api/v1/templates
```

### المشكلة: قاعدة البيانات لا تتصل
```bash
# تحقق من DATABASE_URL في .env
# يجب أن يكون: postgresql+asyncpg://postgres:postgres@127.0.0.1:5434/postgres
python -c "from app.config import get_settings; print(get_settings().database_url)"
```

### المشكلة: Token غير صالح
```bash
# أنشئ token جديد
# تأكد من استخدام JWT_SECRET من .env
```

---

## 📊 المتغيرات المهمة

```bash
# من .env
JWT_SECRET="super-secret-jwt-token-with-at-least-32-characters-long"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5434/postgres"
SUPABASE_URL="http://127.0.0.1:54321"

# من Docker/Database
TENANT_ID="45e2bbee-4689-44b9-b803-1ee07f22e168"
USER_ID="b248cc77-fbb9-4b56-a360-d5dcaf5f6938"
EVENT_ID="8f64cfa0-640e-4904-8a26-e03fdbd5e6bc"
```

---

## ✨ نصائح سريعة

✅ استخدم `/docs` في الـ Backend لتوثيق API  
✅ جميع Requests تحتاج `x-tenant-id` header  
✅ جميع Requests تحتاج `Authorization: Bearer TOKEN` header  
✅ استخدم `F12` في الواجهة لرؤية الأخطاء  
✅ تحقق من Console في Backend للتفاصيل  
✅ احفظ Token في متغير بدلاً من كتابته كل مرة  

---

## 🎯 الملخص

| المرحلة | الأمر | الرابط |
|--------|------|--------|
| **تشغيل** | `python -m uvicorn ...` | :8000 |
| **جلب** | `curl /api/v1/templates` | ✅ |
| **إنشاء** | `curl -X POST ...` | ✅ |
| **معاينة** | `curl -X POST .../preview` | ✅ |
| **تحديث** | `curl -X PATCH ...` | ✅ |
| **حذف** | `curl -X DELETE ...` | ✅ |

**الحالة:** 🟢 كل شيء جاهز!

---

**مُحدّث:** 16 مايو 2026 | **الإصدار:** 3.0.0
