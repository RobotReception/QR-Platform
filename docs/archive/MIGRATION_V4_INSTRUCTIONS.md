# تعليمات تنفيذ Migration V4

## نظرة عامة
Migration V4 يحتوي على تحسينات نظام الأحداث بناءً على التقييم الفني الشامل.

## المحتويات
- ✅ إضافة enum `event_status` للكتابة القوية
- ✅ قيود CHECK على جدول events
- ✅ حقول soft delete (deleted_at, deleted_by)
- ✅ حقول السعة (capacity, vip_capacity, normal_capacity)
- ✅ جدول event_assets جديد
- ✅ عمود token_hash في invitations للأمان
- ✅ دالة transition_event_status للتحكم في workflow

## طريقة التنفيذ (الموصى بها)

### الخطوة 1: افتح Supabase Dashboard
اذهب إلى: https://app.supabase.com/project/vyzvvtyszwbefgkzgjzd/sql

### الخطوة 2: افتح SQL Editor
من القائمة الجانبية، اختر **SQL Editor**

### الخطوة 3: انسخ محتوى Migration
افتح الملف: `d:\QR\supabase\migration_v4_event_improvements.sql`
انسخ كل المحتوى

### الخطوة 4: الصق ونفذ
الصق المحتوى في SQL Editor
اضغط **RUN** أو **Execute**

### الخطوة 5: تحقق من النتائج
تأكد من عدم وجود أخطاء
ستظهر رسالة نجاح عند اكتمال التنفيذ

## الملفات المحدثة (Backend)

### Python Models
- `d:\QR\app\models\event.py` - إضافة الحقول الجديدة
- `d:\QR\app\models\invitation.py` - إضافة token_hash

### Python Routes
- `d:\QR\app\routes\events.py` - إضافة routes جديدة:
  - `POST /events/{id}/transition` - تغيير حالة الحدث
  - `GET/POST/DELETE /events/{id}/assets` - إدارة الأصول

## الملفات المحدثة (Frontend)

### TypeScript Types
- `d:\QR\frontend\src\features\events\types\index.ts` - إضافة الـ types الجديدة

### API Client
- `d:\QR\frontend\src\features\events\api\eventsApi.ts` - إضافة دوال API الجديدة

## بعد التنفيذ

بعد تنفيذ migration بنجاح، يمكنك:

1. **اختبار workflow الحالات**:
   ```bash
   POST /events/{id}/transition
   Body: {"new_status": "published"}
   ```

2. **إضافة أصول للحدث**:
   ```bash
   POST /events/{id}/assets
   Body: {"asset_type": "cover_image", "file_url": "..."}
   ```

3. **استخدام الحقول الجديدة**:
   - `capacity` - السعة الإجمالية
   - `vip_capacity` - سعة VIP
   - `normal_capacity` - السعة العادية
   - `deleted_at` - تاريخ الحذف الناعم

## استكشاف الأخطاء

### خطأ: "type event_status already exists"
**الحل**: هذا طبيعي إذا تم تنفيذ migration جزئياً. استمر في التنفيذ.

### خطأ: "column already exists"
**الحل**: العمود موجود مسبقاً. استمر في التنفيذ.

### خطأ: "constraint already exists"
**الحل**: القيد موجود مسبقاً. استمر في التنفيذ.

## الدعم

إذا واجهت أي مشاكل، راجع:
- التقرير التحليلي: `C:\Users\mo-alshebly\.windsurf\plans\events-interface-analysis-e1be90.md`
- ملف Migration: `d:\QR\supabase\migration_v4_event_improvements.sql`
