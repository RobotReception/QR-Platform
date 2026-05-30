# 🎯 نظام اختيار القالب والبيانات - دليل شامل متكامل

**التاريخ:** 16 مايو 2026  
**الحالة:** ✅ **جاهز للاستخدام**  
**الإصدار:** 4.1.0

---

## 📋 نظرة عامة

نظام احترافي ومتكامل يوفر تجربة سلسة لإنشاء دعوات مخصصة:

```
┌─────────────────────────────────────────────────────────┐
│                    المسار الكامل                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1️⃣  اختيار القالب                                      │
│        ↓                                                │
│  2️⃣  تحديد مواقع الحقول على القالب                      │
│        ↓                                                │
│  3️⃣  تحميل بيانات الضيوف (Excel)                        │
│        ↓                                                │
│  4️⃣  استخراج البيانات تلقائياً                          │
│        ↓                                                │
│  5️⃣  المعاينة والتأكيد                                 │
│        ↓                                                │
│  6️⃣  إنشاء الدعوات ✅                                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🏗️ المكونات الرئيسية

### 1. TemplateSelectionFlow ✅
**الملف:** `TemplateSelectionFlow.tsx`

المسؤول عن:
- اختيار القالب
- تحميل ملف Excel
- استخراج البيانات
- المعاينة النهائية

### 2. TemplateFieldMapping ✅ (جديد)
**الملف:** `TemplateFieldMapping.tsx`

المسؤول عن:
- عرض معاينة القالب
- تحديد مواقع الحقول
- ربط البيانات مع مواقع العناصر
- التحقق من التعيين كامل

### 3. TemplateSelectionModal ✅
**الملف:** `TemplateSelectionModal.tsx`

المسؤول عن:
- تغليف المكونات في Modal
- إدارة الـ overlay
- التعامل مع الإغلاق

---

## 🔄 المسار الكامل خطوة بخطوة

### Step 1: اختيار القالب

```typescript
// يعرض جميع القوالب المتاحة
// المستخدم يختار واحد
// ✓ التحقق من الاختيار
```

**المخرجات:**
- `selectedTemplateId`
- `selectedTemplateName`

---

### Step 2: ربط حقول القالب 🆕

```typescript
// عرض معاينة لقالب مختار
// عرض جميع العناصر على الصورة
// المستخدم يحدد:
//   - موقع اسم الضيف
//   - موقع التاريخ
//   - موقع الوقت
//   - موقع رقم المقعد
//   - موقع الباركود
```

**الفعاليات:**
```typescript
interface FieldMapping {
  guest_name?: string      // element_id
  event_date?: string      // element_id
  event_time?: string      // element_id
  seat_number?: string     // element_id
  barcode?: string         // element_id
  qr_code?: string         // element_id
}
```

**التحقق:**
- ✅ جميع الحقول المطلوبة محددة
- ✅ لا تكرار في التعيين
- ✅ العناصر موجودة في القالب

---

### Step 3: تحميل ملف Excel

```typescript
// المستخدم يحمل ملف Excel
// الملف يحتوي على:
//   - اسم الضيف
//   - التاريخ
//   - الوقت
//   - رقم المقعد
//   - بيانات إضافية
```

**صيغة الملف:**

| اسم الضيف | التاريخ | الوقت | رقم المقعد | بيانات أخرى |
|-----------|--------|------|-----------|-----------|
| أحمد محمد | 2025-06-15 | 19:00 | A12 | ... |
| فاطمة علي | 2025-06-15 | 19:00 | A13 | ... |

---

### Step 4: استخراج البيانات تلقائياً

```typescript
// الخوارزمية:
// 1. اقرأ الملف
// 2. استخرج أسماء الأعمدة
// 3. ابحث عن تطابق بين أسماء الحقول
//    - اسم الضيف → "guest_name", "اسم الضيف", "name"
//    - التاريخ → "event_date", "التاريخ", "date"
//    - الوقت → "event_time", "الوقت", "time"
//    - رقم المقعد → "seat_number", "رقم المقعد", "seat"
```

**التحقق:**
- ✅ جميع الحقول المطلوبة موجودة
- ✅ البيانات ليست فارغة
- ✅ صيغة التاريخ صحيحة

---

### Step 5 & 6: المعاينة والإنشاء

```typescript
// عرض أول 5 صفوف من البيانات
// عرض عدد الضيوف الكلي
// زر تأكيد الإنشاء
```

---

## 💻 الكود - مثال عملي

### البدء السريع

```typescript
import { useState } from 'react'
import { TemplateSelectionFlow } from './TemplateSelectionFlow'
import { TemplateSelectionModal } from './TemplateSelectionModal'

function EventInvitationsTab() {
  const [showFlow, setShowFlow] = useState(false)

  const handleFlowComplete = async (data) => {
    console.log('Data received:', data)
    // {
    //   templateId: '...',
    //   templateName: '...',
    //   guests: [
    //     { guest_name: '...', event_date: '...', ... }
    //   ],
    //   columnMapping: { ... }
    // }

    // إنشاء الدعوات
    await invitationsApi.generateFast({
      event_id: event.id,
      invitations: data.guests.map(g => ({
        guest_name: g.guest_name,
        ticket_class: 'normal'
      })),
      generate_pdf: true,
      generate_zip: true
    })

    setShowFlow(false)
  }

  return (
    <>
      <button 
        className="btn btn-primary"
        onClick={() => setShowFlow(true)}
      >
        🎯 اختيار قالب وإنشاء دعوات
      </button>

      <TemplateSelectionModal
        isOpen={showFlow}
        onClose={() => setShowFlow(false)}
      >
        <TemplateSelectionFlow
          eventId={event.id}
          onComplete={handleFlowComplete}
          onCancel={() => setShowFlow(false)}
        />
      </TemplateSelectionModal>
    </>
  )
}
```

---

## 🎨 واجهة المستخدم

### Step 1: اختيار القالب

```
┌──────────────────────────────────────────┐
│ 1️⃣  2️⃣  3️⃣  4️⃣  [Progress Bar]           │
├──────────────────────────────────────────┤
│  اختر قالب الدعوة                        │
│                                          │
│  ┌────────┐  ┌────────┐  ┌────────┐   │
│  │ قالب 1 │  │ قالب 2 │  │ قالب 3 │   │
│  │ [选中]  │  │        │  │        │   │
│  └────────┘  └────────┘  └────────┘   │
│                                          │
│  [إلغاء]                        [التالي] │
└──────────────────────────────────────────┘
```

---

### Step 2: ربط حقول القالب (جديد) 🆕

```
┌──────────────────────────────────────────┐
│ 1️⃣✓ 2️⃣  3️⃣  4️⃣  [Progress Bar]           │
├──────────────────────────────────────────┤
│ معاينة القالب      │ تعيين الحقول       │
│                    │                     │
│ ┌────────────┐    │ اسم الضيف ✓        │
│ │            │    │ [اسم الضيف     ▼] │
│ │  [معاينة]  │    │                    │
│ │            │    │ التاريخ ✓          │
│ │    (صورة)  │    │ [التاريخ        ▼] │
│ │            │    │                    │
│ └────────────┘    │ الوقت              │
│                    │ [-- اختر --      ▼] │
│                    │                    │
│                    │ رقم المقعد ✓       │
│                    │ [رقم المقعد    ▼] │
│                    │                    │
│                    │ الباركود ✓         │
│                    │ [الباركود      ▼] │
│                    │                    │
│ [رجوع]           [تأكيد]               │
└──────────────────────────────────────────┘
```

---

### Step 3: تحميل الملف

```
┌──────────────────────────────────────────┐
│ 1️⃣✓ 2️⃣✓ 3️⃣  4️⃣  [Progress Bar]           │
├──────────────────────────────────────────┤
│ تحميل بيانات الضيوف                     │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │  📁 اسحب الملف أو انقر            │   │
│  │                                   │   │
│  └──────────────────────────────────┘   │
│                                          │
│ تنسيق الملف:                            │
│ ┌──────────────────────────────────┐   │
│ │ اسم الضيف │ التاريخ │ الوقت │ مقعد│   │
│ │ أحمد محمد │ 2025-06-15 │ ... │   │   │
│ └──────────────────────────────────┘   │
│                                          │
│ [رجوع]                        [التالي]  │
└──────────────────────────────────────────┘
```

---

### Step 4: المعاينة

```
┌──────────────────────────────────────────┐
│ 1️⃣✓ 2️⃣✓ 3️⃣✓ 4️⃣  [Progress Bar]           │
├──────────────────────────────────────────┤
│ معاينة النتائج                          │
│                                          │
│ القالب: قالب 1  │  عدد الضيوف: 150    │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ اسم │ التاريخ │ الوقت │ مقعد       │  │
│ ├────────────────────────────────────┤  │
│ │ أحمد│ 2025-06-15 │ 19:00│ A12     │  │
│ │ فاطمة│ 2025-06-15 │ 19:00│ A13    │  │
│ │ محمد│ 2025-06-15 │ 19:00│ B01     │  │
│ │ ... (147 أكثر)                     │  │
│ └────────────────────────────────────┘  │
│                                          │
│ ✓ جميع البيانات جاهزة                   │
│                                          │
│ [رجوع]                    [إنشاء الدعوات]│
└──────────────────────────────────────────┘
```

---

## 🔄 تدفق البيانات

```
User Input
    ↓
┌─────────────────┐
│ Select Template │ → selectedTemplateId, selectedTemplateName
└─────────────────┘
    ↓
┌─────────────────────────┐
│ Map Template Fields 🆕  │ → fieldMapping (element_id mappings)
└─────────────────────────┘
    ↓
┌─────────────────┐
│ Upload Excel    │ → excelRows (raw data)
└─────────────────┘
    ↓
┌──────────────────────────┐
│ Auto-Extract Columns    │ → columnMapping (column name mappings)
└──────────────────────────┘
    ↓
┌──────────────────┐
│ Validate Mapping│ → errors (if any)
└──────────────────┘
    ↓
┌──────────────────┐
│ Preview & Confirm│
└──────────────────┘
    ↓
onComplete(data) {
  templateId
  templateName
  guests []
  columnMapping {}
  fieldMapping {}  ← NEW
}
    ↓
API: generateFast()
    ↓
✅ Invitations Created
```

---

## 🧪 الاختبار

### Test Case 1: تدفق كامل

```typescript
test('Complete flow: select template -> map fields -> upload -> create', () => {
  // 1. User selects template
  selectTemplate('template-1')
  
  // 2. User maps fields
  mapField('guest_name', 'element-1')
  mapField('event_date', 'element-2')
  mapField('event_time', 'element-3')
  mapField('seat_number', 'element-4')
  mapField('barcode', 'element-5')
  
  // 3. User uploads Excel
  uploadFile('data.xlsx')
  
  // 4. System auto-extracts data
  expect(columnMapping).toEqual({
    guest_name: 'اسم الضيف',
    event_date: 'التاريخ',
    // ...
  })
  
  // 5. User confirms
  confirm()
  
  // 6. Data is passed to API
  expect(onComplete).toBeCalledWith({
    templateId: 'template-1',
    guests: [...]
  })
})
```

---

## 📊 الملفات المضافة

```
frontend/src/features/events/components/
├── TemplateSelectionFlow.tsx         ✅ (موجود)
├── template-selection-flow.css       ✅ (موجود)
├── TemplateSelectionModal.tsx        ✅ (موجود)
├── template-selection-modal.css      ✅ (موجود)
├── TemplateFieldMapping.tsx          ✅ (جديد) 🆕
├── template-field-mapping.css        ✅ (جديد) 🆕
└── [سيتم دمج جميعها]
```

---

## 🚀 الخطوات التالية

### 1. دمج المكونات

```typescript
// في TemplateSelectionFlow
import { TemplateFieldMapping } from './TemplateFieldMapping'

// أضف step جديد
const [currentStep, setCurrentStep] = useState<'template' | 'mapping' | 'upload' | 'preview'>('template')
```

### 2. تحديث المنطق

```typescript
// في Step 1: اختيار القالب
const handleTemplateNext = () => {
  setCurrentStep('mapping')  // اذهب إلى mapping بدلاً من upload
}

// في Step 2: ربط الحقول (جديد)
const handleMappingComplete = (mapping: FieldMapping) => {
  setFieldMapping(mapping)
  setCurrentStep('upload')
}
```

### 3. التكامل الكامل

```typescript
// المسار النهائي:
template → mapping 🆕 → upload → preview → create
```

---

## ✅ Checklist

- [ ] تثبيت المكونات الجديدة
- [ ] دمج TemplateFieldMapping مع TemplateSelectionFlow
- [ ] تحديث المنطق والحالة
- [ ] اختبار المسار الكامل
- [ ] اختبار الاستخراج التلقائي
- [ ] اختبار التحقق من الأخطاء
- [ ] اختبار على أجهزة مختلفة

---

**آخر تحديث:** 16 مايو 2026  
**الإصدار:** 4.1.0  
**الحالة:** ✅ جاهز للدمج
