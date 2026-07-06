# دليل التكامل: نظام استيراج Excel الديناميكي 🚀

## 📍 الملفات المُنشأة

### 1. Services
- **`frontend/src/features/events/services/ExcelImportService.ts`**
  - معالجة ملفات Excel الديناميكية
  - كشف الأعمدة التلقائي
  - تحويل البيانات إلى صيغة API

### 2. Components
- **`frontend/src/features/events/components/ExcelImportDialog.tsx`**
  - واجهة محترفة لاستيراج الملفات
  - معاينة البيانات
  - عرض الأخطاء والتحذيرات

- **`frontend/src/features/events/components/DynamicTextColumnSelector.tsx`**
  - Dropdown ديناميكي لاختيار الأعمدة
  - بحث وتصفية الأعمدة
  - دعم متعدد اللغات

### 3. Styles
- **`frontend/src/features/events/styles/excel-import-dialog.css`**
- **`frontend/src/features/events/styles/dynamic-text-selector.css`**

---

## 🔌 كيفية التكامل

### الخطوة 1: استيراج المكونات في EventBarcodesTab.tsx

```typescript
import { ExcelImportDialog } from '../components/ExcelImportDialog'
import { useState } from 'react'

export function EventBarcodesTab({ event, stats, onlyHistory = false }: Props) {
  const [showExcelImport, setShowExcelImport] = useState(false)
  const [importedData, setImportedData] = useState(null)

  // ... باقي الكود الحالي ...

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* ... content ... */}

      {/* فتح dialog الاستيراج */}
      <button 
        onClick={() => setShowExcelImport(true)}
        className="excel-import-trigger-btn"
      >
        📊 استيراج من Excel
      </button>

      {/* Dialog */}
      {showExcelImport && (
        <ExcelImportDialog
          eventId={event.id}
          onImportComplete={(data) => {
            setImportedData(data)
            setShowExcelImport(false)
            // يمكنك الآن استخدام data.invitations للتوليد
          }}
          onClose={() => setShowExcelImport(false)}
          remainingVip={remainingVip}
          remainingNormal={remainingNormal}
        />
      )}

      {/* أو يمكنك استخدام البيانات المستوردة */}
      {importedData && (
        <div>
          <h4>بيانات مستوردة: {importedData.invitations.length} دعوة</h4>
          {/* عرض المعلومات */}
        </div>
      )}
    </div>
  )
}
```

### الخطوة 2: تحديث محرر الدعوات (EventDesignEditorPage.tsx)

```typescript
import { DynamicTextColumnSelector, AvailableColumn } from '../components/DynamicTextColumnSelector'

// عند إضافة نص ديناميكي:
function addDynamicTextElement() {
  const newElement = createDefaultElement('dynamic_text', elements.length)
  
  // تمرير الأعمدة المتاحة
  newElement.availableColumns = importedData?.availableColumns || []
  
  setElements([...elements, newElement])
}

// في الـ JSX:
{selectedElement?.element_type === 'dynamic_text' && (
  <div className="element-property">
    <label>اختر العمود (Data Source)</label>
    <DynamicTextColumnSelector
      value={selectedElement.data_key || null}
      onChange={(key) => updateElement({ ...selectedElement, data_key: key })}
      columns={convertColumnsToAvailable(importedData?.availableColumns || [])}
    />
  </div>
)}

// دالة تحويل
function convertColumnsToAvailable(columns: string[]): AvailableColumn[] {
  return columns.map(col => ({
    label: col,
    key: `guest.custom_fields.${col}`,
    type: 'text',
    category: 'custom'
  }))
}
```

---

## 📊 مثال على البيانات المُسترجعة

### Input (ملف Excel)
```
| اسم الضيف | عدد الدعوات | نوع التذكرة | رقم الهاتف   | البريد              |
|-----------|-----------|-----------|------------|-------------------|
| أحمد      | 2         | VIP       | 0501234567 | ahmed@example.com |
| فاطمة     | 1         | normal    | 0555555555 | fatima@example.com|
| محمد      |           | vip       | 0566666666 | -                 |
```

### Output (ExcelImportResult)
```json
{
  "status": "warning",
  "totalRows": 3,
  "validRows": 3,
  "invalidRows": 0,
  "columnMappings": [
    {
      "columnIndex": 0,
      "columnName": "اسم الضيف",
      "fieldType": "mandatory",
      "mappedTo": "guest_name",
      "detectedAs": "اسم الضيف"
    },
    {
      "columnIndex": 1,
      "columnName": "عدد الدعوات",
      "fieldType": "optional-known",
      "mappedTo": "invitation_count",
      "detectedAs": "عدد الدعوات"
    },
    {
      "columnIndex": 2,
      "columnName": "نوع التذكرة",
      "fieldType": "optional-known",
      "mappedTo": "ticket_class",
      "detectedAs": "نوع التذكرة"
    },
    {
      "columnIndex": 3,
      "columnName": "رقم الهاتف",
      "fieldType": "custom",
      "mappedTo": "phone",
      "detectedAs": "رقم الهاتف"
    },
    {
      "columnIndex": 4,
      "columnName": "البريد",
      "fieldType": "custom",
      "mappedTo": "email",
      "detectedAs": "البريد الإلكتروني"
    }
  ],
  "availableCustomColumns": ["phone", "email"],
  "parsedData": [
    {
      "rowIndex": 2,
      "guestName": "أحمد",
      "invitationCount": 2,
      "ticketClass": "vip",
      "customFields": {
        "phone": "0501234567",
        "email": "ahmed@example.com"
      },
      "warnings": [],
      "isValid": true
    },
    // ...
  ],
  "globalWarnings": [
    "السطر 4: عدد الدعوات فارغ → سيتم استخدام 1"
  ],
  "globalErrors": [],
  "statistics": {
    "vipCount": 3,
    "normalCount": 1,
    "columnsDetected": 5,
    "customFieldsCount": 2
  }
}
```

### Converted to Invitations
```json
{
  "invitations": [
    {
      "guest_name": "أحمد",
      "ticket_class": "vip",
      "custom_fields": {
        "phone": "0501234567",
        "email": "ahmed@example.com"
      }
    },
    {
      "guest_name": "أحمد",
      "ticket_class": "vip",
      "custom_fields": {
        "phone": "0501234567",
        "email": "ahmed@example.com"
      }
    },
    {
      "guest_name": "فاطمة",
      "ticket_class": "normal",
      "custom_fields": {
        "phone": "0555555555",
        "email": "fatima@example.com"
      }
    },
    {
      "guest_name": "محمد",
      "ticket_class": "vip",
      "custom_fields": {
        "phone": "0566666666"
      }
    }
  ],
  "availableColumns": ["phone", "email"],
  "columnMappings": [...]
}
```

---

## 🎯 الميزات الرئيسية

### 1. كشف ذكي للأعمدة
```typescript
// يدعم أسماء متعددة:
// ✅ اسم الضيف, name, guest_name, full_name
// ✅ عدد الدعوات, invitation_count, count, qty
// ✅ نوع التذكرة, ticket_class, class, type
// ✅ رقم الهاتف, phone, tel, mobile
// ✅ البريد, email, e-mail, mail
```

### 2. معالجة ذكية للأخطاء
```typescript
// القيم الافتراضية مع تحذيرات:
if (invitationCount is invalid) → 1 + warning
if (ticketClass is unclear) → "normal" + warning

// البيانات الفارغة:
if (customField is empty) → محذوف من custom_fields
```

### 3. واجهة احترافية
- ✅ Status alerts (نجاح، تحذير، خطأ)
- ✅ Collapsible sections للبيانات الكثيرة
- ✅ معاينة مباشرة للبيانات
- ✅ إحصائيات شاملة
- ✅ رسائل خطأ واضحة وقابلة للفهم

### 4. Dynamic Column Selector
- ✅ Dropdown مع بحث
- ✅ تجميع حسب النوع (معياري/إضافي)
- ✅ عرض رموز للأنواع المختلفة
- ✅ تحديد سريع

---

## 🔒 معالجة الأمان والبيانات

### Validation في ExcelImportService:
```typescript
// 1. تحقق من العمود الإلزامي
if (!guestName) return invalid

// 2. تحقق من نطاق الأرقام
if (invitationCount < 1 || > 100) return warning

// 3. تطبيع القيم
normalize whitespace, trim(), lowercase for comparisons

// 4. حفظ البيانات الإضافية بأمان
customFields are stored as-is, no validation needed
```

---

## 📝 رسائل الخطأ والتحذيرات المحسّنة

### عند مشاكل في العمود الإلزامي:
```
❌ العمود "اسم الضيف" غير موجود في الملف.
الأعمدة المتاحة: guest_name, name, full_name
```

### عند القيم الافتراضية:
```
⚠ السطر 45: عدد الدعوات فارغ → سيتم استخدام 1
⚠ السطر 89: نوع التذكرة "كبير" غير واضح → سيتم استخدام "عادي"
```

### عند تجاوز الحصة:
```
✗ دعوات VIP المخطط (50) تتجاوز المتاح (30)
```

---

## 🎨 CSS Classes المتاحة

للتخصيص الإضافي:
- `.excel-dialog-overlay`
- `.excel-dialog`
- `.excel-status-alert--success|warning|error`
- `.excel-stat-card`
- `.excel-column-item--mandatory|optional-known|custom`
- `.dynamic-selector__trigger`
- `.dynamic-selector__option--selected`

---

## 🧪 اختبار النظام

### حالات الاختبار الموصى بها:

1. **ملف صحيح تماماً:**
   - جميع الأعمدة موجودة
   - جميع البيانات صحيحة
   - النتيجة: ✅ نجاح

2. **ملف فيه تحذيرات:**
   - بعض القيم افتراضية
   - بعض البيانات الإضافية فارغة
   - النتيجة: ⚠️ تحذير لكن يعمل

3. **ملف فيه أخطاء:**
   - العمود الإلزامي مفقود
   - عدد صفوف صفر
   - النتيجة: ❌ خطأ

4. **ملف مع بيانات إضافية:**
   - أعمدة مخصصة غير معروفة
   - النتيجة: ✅ يتم حفظها كـ custom_fields

---

## 🚀 خطوات التنفيذ التالية

1. ✅ استيراج المكونات
2. ✅ تحديث EventBarcodesTab.tsx
3. ✅ تحديث EventDesignEditorPage.tsx
4. ✅ اختبار كل حالة استخدام
5. ✅ تحديث Backend إذا لزم الأمر

---

## 📞 Support

للأسئلة أو المشاكل:
- تحقق من رسائل الخطأ في الواجهة
- راجع ExcelImportService.ts للمنطق
- تحقق من CSS classes للتنسيق
