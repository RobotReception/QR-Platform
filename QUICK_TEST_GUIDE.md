# 🧪 دليل الاختبار السريع

**التاريخ:** 16 مايو 2026

---

## ⚡ اختبار سريع (5 دقائق)

### الخطوة 1: المصادقة ✅

```
1. افتح: http://localhost:5173
2. اضغط F12 (Developer Tools)
3. انسخ والصق في Console:
```

```javascript
localStorage.setItem('qentry_access_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiMjQ4Y2M3Ny1mYmI5LTRiNTYtYTM2MC1kNWRjYWY1ZjY5MzgiLCJlbWFpbCI6Im93bmVyQGV4YW1wbGUuY29tIiwiYXVkIjoiYXV0aGVudGljYXRlZCIsInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiaWF0IjoxNzc4OTEwNDExLCJleHAiOjE3Nzg5OTY4MTF9.viWaK7GFvZlluzd_2uWvMn9xcGoWCvzd4Ur4gzryIXE');
localStorage.setItem('qentry_tenant_id', '45e2bbee-4689-44b9-b803-1ee07f22e168');
localStorage.setItem('qentry_user', 'b248cc77-fbb9-4b56-a360-d5dcaf5f6938');
location.reload();
```

**النتيجة المتوقعة:**
```
✅ الصفحة تعيد التحميل
✅ لا توجد رسالة خطأ حمراء في Console
✅ الواجهة تحمل بدون مشاكل
```

---

### الخطوة 2: عرض القوالب ✅

```
1. اذهب إلى "الأحداث" (Events)
2. انقر على أي حدث
3. اختر تبويب "قوالب الحدث" (Event Templates)
```

**النتيجة المتوقعة:**
```
✅ القوالب تظهر في شبكة (grid)
✅ بدون خطأ 403
✅ بدون خطأ 401
✅ بدون أخطاء في Console
```

---

### الخطوة 3: اختبار الباركود ✅

```
1. اختر أي قالب
2. اضغط على زر "المعاينة" (Eye icon)
3. انتظر حتى تحميل الصورة
```

**النتيجة المتوقعة:**
```
✅ الباركود يظهر في مكانه الصحيح
✅ لا يظهر معكوساً
✅ الموقع متطابق مع التصميم
✅ بدون تأخير طويل
```

---

### الخطوة 4: تعديل البيانات ✅

```
1. في نافذة المعاينة، غيّر بيانات الاختبار
2. مثلاً: غيّر "اسم الضيف" من "أحمد علي" إلى "محمد علي"
3. اضغط "تحديث المعاينة"
```

**النتيجة المتوقعة:**
```
✅ الصورة تحدّث بالبيانات الجديدة
✅ النص يظهر بشكل صحيح
✅ الباركود ينحدّث تلقائياً
✅ بدون تأخير
```

---

### الخطوة 5: اختبار الحذف ✅

```
1. أغلق نافذة المعاينة
2. اضغط زر "حذف" (Trash icon) على قالب
3. أكّد الحذف في الـ popup
```

**النتيجة المتوقعة:**
```
✅ القالب يُحذف من القائمة
✅ بدون خطأ
✅ القائمة تحدّث تلقائياً
✅ بدون تأخير
```

---

## 🔍 التحقق من الإصلاحات

### اختبار 1: المصادقة (403 Fix) ✅

في Network Tab (F12 → Network):

```
1. اختر أي طلب إلى /templates
2. اذهب إلى Request Headers
3. تحقق من:
   ✅ Authorization: Bearer eyJ...
   ✅ X-Tenant-ID: 45e2bbee-...
   ✅ Content-Type: application/json
```

---

### اختبار 2: موقع الباركود (RTL Fix) ✅

```
1. افتح قالباً يحتوي على باركود
2. في نافذة المعاينة، لاحظ موقع الباركود
3. قارنه مع الموقع في التصميم

النتيجة المتوقعة:
✅ الموقع متطابق تماماً
✅ لا تقليب أو عكس
✅ الجودة عالية
```

---

## ⚠️ استكشاف الأخطاء

### المشكلة: لا تزال 403

**الحل:**
```javascript
// امسح البيانات المخزنة
localStorage.clear();

// ثم أعد:
localStorage.setItem('qentry_access_token', 'TOKEN');
localStorage.setItem('qentry_tenant_id', 'TENANT_ID');
localStorage.setItem('qentry_user', 'USER_ID');
location.reload();
```

---

### المشكلة: الباركود معكوس

**الحل:**
```
1. تأكد من إعادة تحميل الصفحة بـ Ctrl+Shift+R
2. امسح بيانات المتصفح: Settings → Clear browsing data
3. أعد تحميل الصفحة
```

---

### المشكلة: Backend لا يستجيب

**الحل:**
```bash
# تحقق من الخدمة
curl http://127.0.0.1:8000/health

# إذا لم تعمل، أعد تشغيلها:
cd /d/QR
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

### المشكلة: Frontend لا يحمّل

**الحل:**
```bash
# تحقق من الخدمة
curl http://localhost:5173

# إذا لم تعمل، أعد تشغيلها:
cd /d/QR/frontend
npm run dev
```

---

## 📊 Checklist النهائي

| العنصر | ✅ / ❌ |
|--------|--------|
| Authentication يعمل | ✅ |
| Templates تظهر | ✅ |
| Preview يعمل | ✅ |
| Barcode في مكانه | ✅ |
| QR في مكانه | ✅ |
| حذف يعمل | ✅ |
| RTL مدعوم | ✅ |
| LTR مدعوم | ✅ |
| بدون أخطاء Console | ✅ |
| بدون تأخير | ✅ |

---

## 🎉 النتيجة

إذا نجحت جميع الاختبارات أعلاه:

```
🟢 النظام جاهز للاستخدام!
🟢 جميع الميزات تعمل بشكل صحيح
🟢 RTL/LTR مدعوم بشكل كامل
🟢 بدون أخطاء أو تحذيرات
```

---

**استمتع باستخدام النظام! 🚀**
