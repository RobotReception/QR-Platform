# 🔑 دليل الحصول على الوصول - نظام إدارة القوالب

**التاريخ:** 16 مايو 2026  
**الحالة:** ✅ جميع الأنظمة تعمل

---

## ⚠️ الخطأ 403 Forbidden

### المشكلة
```
Request:  GET /api/v1/templates?event_id=...
Response: 403 Forbidden
Message:  "ليس لديك صلاحية: templates.view"
```

### السبب
- بدون Token صحيح
- بدون x-tenant-id في الـ header
- بدون صلاحيات كافية

### الحل
اتبع الخطوات أدناه للحصول على وصول صحيح.

---

## 🚀 الحل - الطريقة السريعة

### الخطوة 1: الحصول على بيانات حقيقية من قاعدة البيانات

```bash
cd D:/QR && python << 'EOF'
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import text

async def get_credentials():
    async with AsyncSessionLocal() as db:
        # الحصول على أول مستأجر مع عضو
        result = await db.execute(text("""
            SELECT 
                t.id as tenant_id,
                t.slug,
                t.name,
                m.user_id,
                m.role
            FROM tenants t
            LEFT JOIN memberships m ON t.id = m.tenant_id
            WHERE m.status = 'active'
            LIMIT 1
        """))
        
        row = result.mappings().first()
        if row:
            print("Tenant ID:", row['tenant_id'])
            print("User ID:", row['user_id'])
            print("Role:", row['role'])
            print("Tenant Name:", row['name'])

asyncio.run(get_credentials())
EOF
```

### الخطوة 2: إنشاء JWT Token

```bash
python << 'EOF'
from jose import jwt
from datetime import datetime, timedelta

JWT_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"
USER_ID = "b248cc77-fbb9-4b56-a360-d5dcaf5f6938"  # من الخطوة 1

payload = {
    "sub": USER_ID,
    "email": "admin@example.com",
    "aud": "authenticated",
    "role": "authenticated",
    "iat": int(datetime.utcnow().timestamp()),
    "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp()),
}

token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
print("TOKEN:", token)
print("USER_ID:", USER_ID)
print("TENANT_ID: 45e2bbee-4689-44b9-b803-1ee07f22e168")
EOF
```

### الخطوة 3: تعيين في localStorage (من Developer Tools)

في المتصفح (F12 → Console):

```javascript
// ضع القيم من الخطوة 2
localStorage.setItem('auth_token', 'TOKEN_HERE');
localStorage.setItem('tenant_id', 'TENANT_ID_HERE');
localStorage.setItem('user_id', 'USER_ID_HERE');

// تحقق
console.log('Token:', localStorage.getItem('auth_token'));
console.log('Tenant ID:', localStorage.getItem('tenant_id'));

// أعد تحميل الصفحة
location.reload();
```

### الخطوة 4: الآن يجب أن يعمل

```
✅ GET /api/v1/templates يجب أن يعيد البيانات
✅ معاينة يجب أن تعمل
✅ تحميل يجب أن يعمل
```

---

## 📋 قائمة التحقق

قبل الاستخدام تأكد من:

```
✅ Backend يعمل على http://127.0.0.1:8000
✅ Frontend يعمل على http://localhost:5174
✅ Database يعمل على 127.0.0.1:5434
✅ لديك TOKEN صحيح
✅ لديك TENANT_ID صحيح
✅ لديك USER_ID صحيح
✅ Token وضع في localStorage
```

---

## 🔍 استكشاف المشاكل

### المشكلة 1: 403 - بدون صلاحية

**الحل:**
```bash
# تحقق من أن المستخدم عضو في المستأجر
curl -H "Authorization: Bearer TOKEN" \
     -H "x-tenant-id: TENANT_ID" \
     http://127.0.0.1:8000/api/v1/templates

# إذا حصلت على 403 فالمستخدم بدون صلاحية
# جرب استخدام user_id من جدول memberships
```

### المشكلة 2: 401 - Token غير صالح

**الحل:**
```bash
# أنشئ token جديد
# تأكد من استخدام JWT_SECRET من .env
# تأكد من أن sub = user_id موجود
```

### المشكلة 3: null Headers

**الحل:**
```javascript
// تأكد من:
console.log(localStorage.getItem('auth_token'));
console.log(localStorage.getItem('tenant_id'));

// إذا كانت null أعد الخطوات أعلاه
```

---

## 🎯 الخطوات الكاملة (من الصفر)

### 1. التشغيل
```bash
# Terminal 1
cd D:/QR
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2
cd D:/QR/frontend
npm run dev
```

### 2. الحصول على البيانات
```bash
# قم بتشغيل السكريبت من "الخطوة 1" أعلاه
python << 'EOF'
# ... (نسخ الكود من الخطوة 1)
EOF
```

### 3. إنشاء Token
```bash
python << 'EOF'
# ... (نسخ الكود من الخطوة 2)
EOF
```

### 4. فتح الواجهة
```
http://localhost:5174
```

### 5. تعيين البيانات في localStorage
```
F12 → Console → (انسخ الكود من الخطوة 3)
```

### 6. استخدام الميزات
```
Dashboard → الأحداث → قوالب الحدث 🎨
```

---

## ✅ التحقق من النجاح

إذا عملت كل الخطوات يجب أن ترى:

```
✅ القوالب تظهر في الشبكة
✅ يمكن الضغط على معاينة
✅ الصور تحمل بدون أخطاء
✅ يمكن تحميل الصور
✅ يمكن حذف القوالب
✅ بدون 403 أو 401 errors
```

---

## 🔐 معلومات الأمان

### لماذا نحتاج Token؟
- ✅ لحماية البيانات من الوصول غير المصرح
- ✅ لمعرفة من يفعل ماذا
- ✅ لمنع الهجمات
- ✅ لتتبع الأنشطة

### لماذا نحتاج TENANT_ID؟
- ✅ لعزل بيانات الشركات عن بعضها
- ✅ لمنع الوصول لبيانات الآخرين
- ✅ لضمان الخصوصية
- ✅ للتوافق مع الأنظمة المتعددة

---

## 📚 مراجع إضافية

- 📖 `QUICKSTART.md` - البدء السريع
- 📖 `TESTING_GUIDE_AR.md` - اختبارات شاملة
- 📖 `SYSTEM_STATUS_REPORT.md` - حالة النظام

---

## ❓ الأسئلة الشائعة

**س: لماذا 403؟**  
ج: بدون Token صحيح أو بدون صلاحيات

**س: كيف أحصل على Token؟**  
ج: استخدم السكريبت في الخطوة 2

**س: أين أضع Token؟**  
ج: في localStorage أو Authorization header

**س: ماذا لو نسيت TENANT_ID؟**  
ج: استخدم السكريبت في الخطوة 1 للحصول عليه

**س: هل يمكن استخدام أي User ID؟**  
ج: لا، يجب أن يكون عضواً نشطاً في المستأجر

---

## 🎉 الخلاصة

اتبع الخطوات أعلاه وستحصل على وصول كامل للنظام مع جميع الميزات:

✅ معاينة فورية  
✅ تعديل البيانات  
✅ تحميل الصور  
✅ إدارة القوالب  

**الحالة:** 🟢 **جاهز للاستخدام**

---

**للمساعدة:** راجع التوثيق أو اتصل بفريق الدعم

