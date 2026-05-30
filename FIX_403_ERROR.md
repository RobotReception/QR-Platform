# 🔑 حل مشكلة المصادقة 403 - دليل كامل

**التاريخ:** 16 مايو 2026  
**الحالة:** ✅ تم حل المشكلة

---

## ⚠️ المشكلة

```
Request:  GET /api/v1/templates?event_id=...
Status:   403 Forbidden
Error:    Not authenticated
```

---

## ✅ الحل السريع (5 دقائق)

### الطريقة 1️⃣: تطبيق مباشر

#### الخطوة 1: فتح المتصفح

```
اذهب إلى: http://localhost:5173
```

#### الخطوة 2: فتح Developer Tools

```
اضغط: F12
أو: Right Click → Inspect
```

#### الخطوة 3: اذهب إلى Console

```
اختر التبويب: Console
```

#### الخطوة 4: انسخ هذا الكود

```javascript
localStorage.setItem('qentry_access_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiMjQ4Y2M3Ny1mYmI5LTRiNTYtYTM2MC1kNWRjYWY1ZjY5MzgiLCJlbWFpbCI6Im93bmVyQGV4YW1wbGUuY29tIiwiYXVkIjoiYXV0aGVudGljYXRlZCIsInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiaWF0IjoxNzc4OTEwNDExLCJleHAiOjE3Nzg5OTY4MTF9.viWaK7GFvZlluzd_2uWvMn9xcGoWCvzd4Ur4gzryIXE');
localStorage.setItem('qentry_tenant_id', '45e2bbee-4689-44b9-b803-1ee07f22e168');
localStorage.setItem('qentry_user', 'b248cc77-fbb9-4b56-a360-d5dcaf5f6938');
location.reload();
```

#### الخطوة 5: الصق في Console

```
Paste the code
```

#### الخطوة 6: اضغط Enter

```
الصفحة ستُحدّث تلقائياً
```

---

### الطريقة 2️⃣: استخدام ملف HTML

```bash
# افتح الملف في المتصفح
D:\QR\auth-setup.html

# أو اكتب في شريط العناوين
file:///D:/QR/auth-setup.html
```

ثم اتبع التعليمات الموجودة في الصفحة.

---

### الطريقة 3️⃣: تشغيل Batch Script

```bash
# في Windows Command Prompt
cd D:\QR
setup-auth.bat
```

ثم انسخ الكود المعروض والصقه في Console.

---

## 🔍 التحقق من النجاح

بعد تطبيق الخطوات أعلاه، تأكد من:

```javascript
// في Console تحقق من:
console.log('Token:', localStorage.getItem('qentry_access_token'));
console.log('Tenant:', localStorage.getItem('qentry_tenant_id'));
console.log('User:', localStorage.getItem('qentry_user'));

// جميعها يجب أن تُظهر قيم (ليست null أو undefined)
```

### ✅ إذا عملت:
```
✅ القوالب تظهر في الصفحة
✅ بدون أخطاء 403 أو 401
✅ يمكن الضغط على معاينة
✅ يمكن تحميل الصور
✅ يمكن حذف القوالب
```

---

## 🆘 استكشاف الأخطاء

### المشكلة: لا تزال تظهر 403 بعد تطبيق الخطوات

**الحل:**
```javascript
// تأكد من أن البيانات محفوظة
localStorage.clear();
// ثم أعد الخطوات مرة أخرى
localStorage.setItem('qentry_access_token', 'TOKEN');
localStorage.setItem('qentry_tenant_id', 'TENANT_ID');
localStorage.setItem('qentry_user', 'USER_ID');
location.reload();
```

### المشكلة: خطأ "Backend not responding"

**الحل:**
```bash
# تأكد من أن Backend يعمل
curl http://127.0.0.1:8000/health

# إذا لم يعمل، شغل Backend
cd D:/QR
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### المشكلة: لا يمكن الكتابة في localStorage

**الحل:**
```javascript
// قد تكون في Incognito/Private mode
// جرب في Incognito أو عادي؟

// أو امسح بيانات المتصفح
// Settings → Clear browsing data
```

---

## 📋 البيانات المستخدمة

### Credentials المستخدمة

```
Token:     eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Tenant ID: 45e2bbee-4689-44b9-b803-1ee07f22e168
User ID:   b248cc77-fbb9-4b56-a360-d5dcaf5f6938
Role:      owner
```

### معلومات تفصيلية

```
JWT Algorithm:     HS256
Token Expiry:      24 ساعة
Tenant Role:       Owner (جميع الصلاحيات)
Status:            Active
```

---

## 🎯 ماذا يحدث الآن؟

بعد تطبيق خطوات المصادقة:

```
1. ✅ Frontend يحفظ Token في localStorage
2. ✅ axios interceptor يُضيف Token لكل request
3. ✅ Backend يتحقق من Token
4. ✅ Backend يتحقق من الصلاحيات
5. ✅ API ترجع البيانات
6. ✅ القوالب تظهر في الواجهة
```

---

## 📚 المراجع

- 📖 `GETTING_ACCESS.md` - دليل الوصول الشامل
- 📖 `QUICKSTART.md` - البدء السريع
- 📖 `TESTING_GUIDE_AR.md` - دليل الاختبارات

---

## ✨ الميزات المتاحة الآن

بعد تسجيل الدخول:

```
✅ معاينة فورية للقوالب
✅ تعديل البيانات الحية
✅ تحميل صور PNG
✅ حذف آمن مع تأكيد
✅ إدارة كاملة للقوالب
✅ نظام أمان محكم
```

---

## 🔐 معلومات الأمان

### لماذا نحتاج Token؟
- يحمي API من الوصول غير المصرح
- يتحقق من هويتك
- يسجل أنشطتك

### هل Token آمن؟
- ✅ نعم، مشفر بـ HS256
- ✅ ينتهي بعد 24 ساعة
- ✅ يُحفظ في localStorage (آمن للاختبار)

---

## 🎊 الآن يجب أن يعمل!

```
✅ جميع الخدمات تعمل
✅ المصادقة جاهزة
✅ الصلاحيات مُعطاة
✅ لا أخطاء 403
```

**استمتع باستخدام النظام! 🎉**

---

**للمساعدة:** راجع الملفات أعلاه أو اسأل في Developer Console (F12)

