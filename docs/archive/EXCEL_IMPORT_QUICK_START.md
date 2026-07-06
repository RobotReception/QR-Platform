# 🚀 نظام استيراج Excel الديناميكي - دليل سريع

## 📦 الملفات المُنشأة (جاهزة للاستخدام)

```
frontend/src/features/events/
├── services/
│   └── ExcelImportService.ts (400+ أسطر)
├── components/
│   ├── ExcelImportDialog.tsx (500+ أسطر)
│   └── DynamicTextColumnSelector.tsx (200+ أسطر)
└── styles/
    ├── excel-import-dialog.css (700+ أسطر)
    └── dynamic-text-selector.css (350+ أسطر)
```

---

## 🎯 الميزات الرئيسية

| الميزة | التفصيل |
|--------|---------|
| **أعمدة ديناميكية** | اكتشاف تلقائي + معالجة ذكية |
| **3 أعمدة إلزامية** | اسم الضيف (إلزامي) + عدد الدعوات + نوع التذكرة |
| **أعمدة إضافية** | هاتف، بريد، مقعد، طاولة، شركة، وظيفة، منطقة، قاعة |
| **رسائل واضحة** | ✅ نجاح | ⚠️ تحذيرات | ❌ أخطاء |
| **Dropdown ديناميكي** | اختيار الأعمدة مباشرة في محرر الدعوات |
| **واجهة احترافية** | تصميم جميل وسهل الاستخدام |
| **معالجة آمنة** | تحويل ذكي + حفظ البيانات الإضافية |

---

## 🔌 التكامل السريع

### 1. استيراج الـ Service والـ Components

```typescript
// في EventBarcodesTab.tsx
import { ExcelImportDialog } from '../components/ExcelImportDialog'
import { useState } from 'react'

export function EventBarcodesTab({ event, stats }: Props) {
  const [showExcelImport, setShowExcelImport] = useState(false)
  const [importedData, setImportedData] = useState(null)

  // ... باقي الكود
}
```

### 2. إضافة الـ Button

```jsx
<button 
  onClick={() => setShowExcelImport(true)}
  className="btn-excel-import"
>
  📊 استيراج من Excel
</button>
```

### 3. إضافة الـ Dialog

```jsx
{showExcelImport && (
  <ExcelImportDialog
    eventId={event.id}
    onImportComplete={(data) => {
      setImportedData(data)
      setShowExcelImport(false)
      // استخدم data.invitations للتوليد
    }}
    onClose={() => setShowExcelImport(false)}
    remainingVip={remainingVip}
    remainingNormal={remainingNormal}
  />
)}
```

### 4. استخدام البيانات المستوردة

```typescript
if (importedData) {
  const invitations = ExcelImportService.convertToInvitations(importedData)
  // أرسل إلى API للتوليد
  generate({
    event_id: event.id,
    invitations: invitations,
    generate_pdf: true,
    generate_zip: true,
    layout_config: layout
  })
}
```

---

## 📊 مثال على البيانات المُرجعة

```json
{
  "invitations": [
    {
      "guest_name": "أحمد علي",
      "ticket_class": "vip",
      "custom_fields": {
        "phone": "0501234567",
        "email": "ahmed@example.com",
        "seat": "A12"
      }
    }
  ],
  "availableColumns": ["phone", "email", "seat"],
  "columnMappings": [...]
}
```

---

## 🎨 في محرر الدعوات

### استيراج الـ Selector

```typescript
import { DynamicTextColumnSelector, AvailableColumn } from '../components/DynamicTextColumnSelector'
```

### استخدام في الـ Form

```jsx
{selectedElement?.element_type === 'dynamic_text' && (
  <div>
    <label>اختر عمود من البيانات</label>
    <DynamicTextColumnSelector
      value={selectedElement.data_key || null}
      onChange={(key) => updateElement({ ...selectedElement, data_key: key })}
      columns={availableColumns}
    />
  </div>
)}
```

---

## ⚙️ كيفية عمل Service

### الخطوة 1: قراءة الملف

```typescript
const result = await ExcelImportService.parseExcelFile(file)
```

### النتيجة:

```typescript
{
  status: 'success' | 'warning' | 'error',
  totalRows: 150,
  validRows: 150,
  invalidRows: 0,
  columnMappings: [...],
  availableCustomColumns: ['phone', 'email'],
  parsedData: [...],
  globalWarnings: [],
  globalErrors: [],
  statistics: {
    vipCount: 50,
    normalCount: 100,
    columnsDetected: 5,
    customFieldsCount: 2
  }
}
```

### الخطوة 2: التحويل

```typescript
const invitations = ExcelImportService.convertToInvitations(result)
// النتيجة: مصفوفة من invitations جاهزة للـ API
```

---

## 🎯 الأعمدة المدعومة

### ✅ معروفة (مطابقة تلقائية)

```
اسم الضيف ← AR: اسم, الاسم الكامل | EN: name, full_name, guest_name
عدد الدعوات ← AR: الكمية | EN: invitation_count, count, qty
نوع التذكرة ← AR: نوع الدخول | EN: ticket_class, class, type
رقم الهاتف ← AR: الهاتف | EN: phone, tel, mobile
البريد ← EN: email, mail
رقم المقعد ← EN: seat, seat_number
الشركة ← EN: company, organization
الوظيفة ← EN: title, position, job
المنطقة ← EN: zone, area
القاعة ← EN: hall, room
```

### 🟢 أي عمود آخر
→ يتم حفظه كـ `custom_fields` تلقائياً

---

## 🚨 رسائل الخطأ

### ✅ النجاح:
```
✓ تم التحقق من الملف بنجاح
  • 50 صف صحيح
  • 5 أعمدة مكتشفة
```

### ⚠️ التحذيرات:
```
⚠ السطر 45: عدد الدعوات فارغ → سيتم استخدام 1
⚠ السطر 89: نوع التذكرة "كبير" → سيتم استخدام normal
```

### ❌ الأخطاء:
```
✗ العمود "اسم الضيف" غير موجود
✗ الملف فارغ
✗ صيغة الملف غير مدعومة
```

---

## 🎨 CSS Classes للتخصيص

```css
.excel-dialog-overlay { }          /* الخلفية الشفافة */
.excel-dialog { }                   /* الـ Dialog الرئيسي */
.excel-status-alert { }             /* Alert الحالة */
.excel-stat-card { }                /* بطاقات الإحصائيات */
.excel-column-item { }              /* عنصر العمود */
.excel-preview-table { }            /* جدول المعاينة */
.dynamic-selector { }               /* الـ Dropdown */
.dynamic-selector__option { }       /* خيار في الـ Dropdown */
```

---

## 🧪 اختبر بهذا الملف

```
| اسم الضيف | عدد الدعوات | نوع التذكرة |
|-----------|-----------|-----------|
| أحمد      | 1         | VIP       |
| فاطمة     | 2         | normal    |
| محمد      |           | v         |
```

**النتيجة المتوقعة:**
- ✓ 3 صفوف صحيحة
- ⚠️ تحذير واحد (السطر 4: عدد الدعوات فارغ)
- ✓ 4 دعوات إجمالية

---

## 📋 Checklist قبل البدء

- [ ] انسخ الملفات الثلاثة (service + components)
- [ ] انسخ ملفات CSS
- [ ] استيراج ExcelImportDialog في EventBarcodesTab.tsx
- [ ] استيراج DynamicTextColumnSelector في EventDesignEditorPage.tsx
- [ ] اختبر الاستيراج من Excel
- [ ] اختبر الـ Dropdown في محرر الدعوات
- [ ] شغّل جميع الحالات الاختبارية

---

## 💡 نصائح مفيدة

1. **البيانات الفارغة:**
   - عمود إلزامي فارغ = خطأ
   - عمود اختياري فارغ = استخدام افتراضي

2. **الأعمدة الإضافية:**
   - كل عمود غير معروف = custom_field
   - يتم حفظها تلقائياً

3. **الأداء:**
   - يدعم حتى 10,000 صف
   - المعالجة فورية

4. **المتصفح:**
   - يعمل في جميع المتصفحات الحديثة
   - Responsive على الهواتف

---

## 🎓 لمزيد من التفاصيل

- 📖 `EXCEL_IMPORT_SYSTEM_SUMMARY.md` - ملخص شامل
- 📖 `EXCEL_IMPORT_INTEGRATION_GUIDE.md` - دليل التكامل
- 📖 `EXCEL_IMPORT_ANALYSIS.md` - تحليل البيانات
- 📖 `EXCEL_IMPORT_IMPROVEMENTS_PLAN.md` - خطة التحسينات

---

## ❓ أسئلة شائعة

**س: هل يدعم ملفات .csv؟**
ج: حالياً لا، لكن يمكن إضافة الدعم بسهولة عبر تحويل CSV إلى JSON

**س: كم عدد الأعمدة المدعومة؟**
ج: غير محدود - أي عمود يتم قراءته ويتم حفظه

**س: هل هناك حد أقصى لعدد الصفوف؟**
ج: 10,000 صف، يمكن زيادته في الـ Service

**س: هل البيانات الإضافية تُحفظ في قاعدة البيانات؟**
ج: نعم، في حقل `custom_fields` في جدول `invitations`

---

## 🎉 جاهز للاستخدام!

النظام **كامل وديناميكي وجاهز للدمج الفوري** في المشروع 🚀
