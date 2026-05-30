# 🎨 ميزة معاينة القالب قبل الطباعة

## 📋 نظرة عامة

تم إضافة ميزة جديدة تسمح للمستخدمين برؤية معاينة القالب قبل طباعة الدعوات. المعاينة تظهر كيف ستبدو الدعوة الفعلية مع بيانات اختبارية.

---

## 🔌 API Endpoint

### معاينة القالب

**POST** `/api/v1/templates/{template_id}/preview`

**الوصف:** جلب معاينة PNG للقالب مع بيانات اختبارية

#### Body Parameters:

```json
{
  "guest_name": "أحمد علي",           // اسم الضيف (اختياري)
  "event_title": "حفل تخرج",          // عنوان الحفل (اختياري)
  "event_date": "2025-06-15",         // تاريخ الحفل (اختياري)
  "event_time": "19:00",              // وقت الحفل (اختياري)
  "event_location": "فندق الريتز",    // مكان الحفل (اختياري)
  "seat_number": "A12",               // رقم المقعد (اختياري)
  "table_number": "5",                // رقم الطاولة (اختياري)
  "custom_data": {}                   // بيانات إضافية مخصصة (اختياري)
}
```

#### الاستجابة:

- **Status:** 200 OK
- **Content-Type:** `image/png`
- **Body:** صورة PNG للدعوة المعاينة

#### أمثلة الأخطاء:

| الحالة | الكود | الرسالة |
|--------|------|---------|
| القالب غير موجود | 404 | "القالب غير موجود" |
| لا توجد خلفية | 400 | "القالب لا يحتوي على خلفية" |
| خطأ في التحميل | 500 | "خطأ في تحميل الخلفية" |
| خطأ في الرسم | 500 | "خطأ في رسم المعاينة" |

---

## 💻 أمثلة الاستخدام

### مع cURL:

```bash
curl -X POST http://localhost:8000/api/v1/templates/{TEMPLATE_ID}/preview \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: YOUR_TENANT_ID" \
  -d '{
    "guest_name": "محمد أحمد",
    "event_title": "حفل الزفاف",
    "event_date": "2025-07-20",
    "event_time": "20:00",
    "event_location": "قاعة النيل"
  }' \
  --output preview.png
```

### مع JavaScript/Fetch:

```javascript
const response = await fetch(
  `/api/v1/templates/${templateId}/preview`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'x-tenant-id': tenantId,
    },
    body: JSON.stringify({
      guest_name: 'أحمد علي',
      event_title: 'حفل تخرج',
      event_date: '2025-06-15',
      event_time: '19:00',
      event_location: 'فندق الريتز',
      seat_number: 'A12',
      table_number: '5',
    }),
  }
);

const blob = await response.blob();
const imageUrl = URL.createObjectURL(blob);

// عرض المعاينة
document.getElementById('preview').src = imageUrl;
```

### مع Python/Requests:

```python
import requests

url = f"http://localhost:8000/api/v1/templates/{template_id}/preview"
headers = {
    'Authorization': f'Bearer {token}',
    'x-tenant-id': tenant_id,
}
data = {
    'guest_name': 'أحمد علي',
    'event_title': 'حفل تخرج',
    'event_date': '2025-06-15',
    'event_time': '19:00',
    'event_location': 'فندق الريتز',
    'seat_number': 'A12',
    'table_number': '5',
}

response = requests.post(url, json=data, headers=headers)

# حفظ الصورة
with open('preview.png', 'wb') as f:
    f.write(response.content)
```

---

## 🎯 حالات الاستخدام

### 1. معاينة سريعة أثناء التصميم
```javascript
// عندما يحفظ المستخدم التصميم، اعرض معاينة
const preview = await templateService.previewTemplate(templateId, {
  guest_name: 'تصميم اختبار',
  event_title: template.event_title,
});
```

### 2. مراجعة قبل الطباعة
```javascript
// قبل إنشاء دفعة الطباعة
const preview = await templateService.previewTemplate(templateId);
// عرض المعاينة للمستخدم للتأكد
```

### 3. معاينات متعددة بأحجام مختلفة
```javascript
const previews = await Promise.all([
  templateService.previewTemplate(templateId, { guest_name: 'ضيف 1' }),
  templateService.previewTemplate(templateId, { guest_name: 'ضيف 2' }),
  templateService.previewTemplate(templateId, { guest_name: 'ضيف 3' }),
]);
```

---

## 🔍 كيفية يعمل في الخلفية

### العملية:

1. **جلب بيانات القالب** من قاعدة البيانات
   - معلومات القالب (الأبعاد، الألوان)
   - عناصر القالب (نصوص، أكواد QR، صور)

2. **جلب صورة الخلفية** من Supabase Storage
   - التحقق من وجود الخلفية
   - تحميل الصورة

3. **بناء السياق** من البيانات المرسلة
   ```python
   context = {
       "guest": {"name": "أحمد علي", ...},
       "event": {"title": "حفل تخرج", ...},
       "invite": {"code": "PREVIEW123", ...},
       "custom": {"seat": "A12", ...},
   }
   ```

4. **رسم الدعوة** باستخدام `render_invitation_image`
   - وضع الخلفية
   - رسم النصوص
   - رسم أكواد QR/Barcode
   - تطبيق التدوير والتأثيرات

5. **إرجاع الصورة** كـ PNG

---

## 🛡️ الصلاحيات والأمان

- ✅ يتطلب **التوثيق** (JWT Token)
- ✅ يتطلب صلاحية **`templates.view`**
- ✅ يتحقق من **ملكية المستأجر** (Tenant)
- ✅ **معاينة آمنة** - لا تُحفظ في قاعدة البيانات
- ✅ **معالجة أخطاء** محكمة

---

## 📊 البيانات الاختبارية الافتراضية

إذا لم تُرسل قيم معينة، تُستخدم القيم الافتراضية:

```python
{
    "guest_name": "أحمد علي",
    "event_title": "حفل تخرج",
    "event_date": "2025-06-15",
    "event_time": "19:00",
    "event_location": "فندق الريتز",
    "seat_number": "A12",
    "table_number": "5",
}
```

---

## 🎨 خصائص المعاينة

المعاينة تحترم جميع خصائص القالب:

| الميزة | الحالة |
|--------|--------|
| موضع العناصر | ✅ محفوظ |
| حجم النص | ✅ محفوظ |
| خطوط النص | ✅ محفوظ |
| ألوان النص | ✅ محفوظ |
| اتجاه النص (RTL/LTR) | ✅ محفوظ |
| أكواد QR | ✅ مرسومة |
| Barcodes | ✅ مرسومة |
| التدوير | ✅ محفوظ |
| الشفافية | ✅ محفوظة |
| الخلفية | ✅ محفوظة |

---

## ⚙️ التكوين

المعاينة تستخدم نفس محرك الرسم المستخدم في إنشاء الدفعات:

```python
# من app/services/render_service.py
render_invitation_image(
    background_bytes=background_bytes,
    elements=elements,
    context=context,
    canvas_width=canvas_width,
    canvas_height=canvas_height,
    background_transform=template_metadata,
    output_format="PNG",
)
```

---

## 🐛 استكشاف الأخطاء

### المشكلة: "القالب لا يحتوي على خلفية"

**الحل:**
1. تأكد من تحميل خلفية للقالب
2. انتقل إلى تعديل القالب
3. ارفع صورة خلفية جديدة

### المشكلة: خطأ في تحميل الخلفية

**الحل:**
1. تحقق من اتصالك بالإنترنت
2. تأكد من أن Supabase Storage يعمل
3. جرب إعادة تحميل الخلفية

### المشكلة: المعاينة تبدو مختلفة عن الطباعة

**الحل:**
1. تحقق من أن جميع العناصر مرئية (`is_visible: true`)
2. تأكد من أن البيانات الاختبارية تطابق البيانات الحقيقية
3. راجع حجم الخط والموضع

---

## 📈 الأداء

- ⚡ **سرعة المعاينة:** عادة 1-3 ثواني
- 💾 **حجم الصورة:** 100-500 KB بناءً على تعقيد القالب
- 🔄 **عدم التخزين المؤقت:** كل معاينة تُرسم حديثاً

---

## 🔄 نسخة API

**Version:** 1.0.0  
**Added:** May 16, 2026  
**Status:** ✅ متاح للاستخدام  

---

## 📚 المراجع

- [تطبيق Render Service](app/services/render_service.py)
- [نموذج Template](app/models/template.py)
- [Routes Templates](app/routes/templates.py)
