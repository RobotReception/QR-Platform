# تحليل شامل: آلية التعامل مع ملفات الإكسل والأعمدة الإلزامية 📊

## 1. معلومات عامة عن نظام الاستيراد

### المكان الرئيسي:
- **Frontend**: `frontend/src/features/events/components/EventBarcodesTab.tsx` (سطر 142-190)
- **Backend**: `app/routes/guests.py` (سطر 133-164)
- **نموذج البيانات**: `app/models/guest.py` و `app/models/invitation.py`

### طريقة الاستيراد:
يستخدم المشروع مكتبة **XLSX** (SheetJS) بدون عتماديات خارجية ثقيلة:
```typescript
import * as XLSX from 'xlsx'  // Frontend
```

---

## 2. الأعمدة الحالية المدعومة والتحقق منها

### الأعمدة المقبولة (مرن جداً):

| الحقل | الأسماء المقبولة (البديل) | النوع | إلزامي؟ | التحقق |
|------|--------------------------|-------|--------|--------|
| **اسم الضيف** | `اسم الضيف`, `guest_name`, `name` | String | ✅ **نعم** | يجب ألا يكون فارغاً، أقل من 255 حرف |
| **عدد الدعوات** | `عدد الدعوات`, `invitation_count`, `count` | Number | ❌ اختياري | من 1-100 (افتراضي: 1) |
| **نوع التذكرة** | `نوع التذكرة`, `ticket_class`, `class` | String | ❌ اختياري | `vip`, `v`, `كبار الشخصيات` → VIP، الباقي → normal |

---

## 3. آلية المعالجة (Processing Logic)

### المرحلة 1: قراءة الملف

```typescript
const buffer = await file.arrayBuffer()
const workbook = XLSX.read(buffer, { type: 'array' })
const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(firstSheet, { defval: '' })
```

**ملاحظات:**
- يتم قراءة **الورقة الأولى فقط** من الملف
- القيم الفارغة تُحل بـ `''` (string فارغ)
- يدعم `.xlsx` و `.xls` فقط (التحقق من خلال attribute `accept=".xlsx,.xls"`)

### المرحلة 2: التحقق من البيانات (Validation)

```typescript
const guestName = String(row['اسم الضيف'] ?? row['guest_name'] ?? row['name'] ?? '').trim()
const invitationCountRaw = row['عدد الدعوات'] ?? row['invitation_count'] ?? row['count'] ?? 1
const invitationCount = Number(invitationCountRaw)
const ticketClass = parseTicketClass(row['نوع التذكرة'] ?? row['ticket_class'] ?? row['class'])

if (!guestName) {
  errors.push(`السطر ${index + 2}: اسم الضيف مفقود`)  // index+2 لأن Excel يبدأ من 1 والهيدر في 1
  return
}

if (!Number.isFinite(invitationCount) || invitationCount < 1 || invitationCount > 100) {
  errors.push(`السطر ${index + 2}: عدد الدعوات يجب أن يكون بين 1 و100`)
  return
}
```

### المرحلة 3: تحليل نوع التذكرة

```typescript
const parseTicketClass = (value: unknown): 'vip' | 'normal' => {
  const normalized = String(value ?? '').trim().toLowerCase()
  if (['vip', 'v', 'كبار الشخصيات'].includes(normalized)) return 'vip'
  return 'normal'  // الافتراضي
}
```

**الخيارات المقبولة لـ VIP:**
- `vip` (إنجليزي)
- `v` (اختصار)
- `كبار الشخصيات` (عربي)
- أي شيء آخر = `normal`

---

## 4. الأخطاء المعالجة والرسائل

| الشرط | رسالة الخطأ | السطر الموضح |
|------|-----------|-------------|
| اسم الضيف فارغ | `السطر X: اسم الضيف مفقود` | نعم ✅ |
| عدد الدعوات غير صحيح | `السطر X: عدد الدعوات يجب أن يكون بين 1 و100` | نعم ✅ |
| لا توجد صفوف صحيحة | `لم يتم العثور على صفوف صالحة داخل الملف` | عام |
| ملف غير صحيح | `تعذر قراءة الملف. استخدم ملف Excel بصيغة .xlsx أو .xls` | عام |

**كيفية العرض:**
- يتم عرض أول **5 أخطاء فقط** (`.slice(0, 5)`)
- الأخطاء تُعرض في مربع أحمر باسم `inv-import-errors`

---

## 5. عملية التحويل إلى الدعوات

### الخطوة 1: التحضير في Frontend

```typescript
const invitations: Array<{ guest_name?: string; ticket_class: 'vip' | 'normal' }> = []
importedGuests.forEach((guest) => {
  for (let i = 0; i < guest.invitation_count; i++) {
    invitations.push({ guest_name: guest.guest_name, ticket_class: guest.ticket_class })
  }
})
```

**مثال:**
```
الضيف "أحمد" مع عدد دعوات = 3 و نوع التذكرة = VIP
↓
ينتج عنه: 3 دعوات بنفس الاسم والنوع
[
  { guest_name: 'أحمد', ticket_class: 'vip' },
  { guest_name: 'أحمد', ticket_class: 'vip' },
  { guest_name: 'أحمد', ticket_class: 'vip' }
]
```

### الخطوة 2: التحقق من الحصص (Quotas)

```typescript
const remainingVip = Math.max(0, event.vip_quota - (stats?.vip_count || 0))
const remainingNormal = Math.max(0, event.normal_quota - (stats?.normal_count || 0))
const isFormValid = (plannedVipCount > 0 || plannedNormalCount > 0) 
  && plannedVipCount <= remainingVip 
  && plannedNormalCount <= remainingNormal
```

**يتم التحقق من:**
- عدد دعوات VIP لا يتجاوز الحصة المتبقية
- عدد الدعوات العادية لا يتجاوز الحصة المتبقية
- وجود دعوة واحدة على الأقل

### الخطوة 3: الإرسال إلى API

```typescript
generate(
  {
    event_id: event.id,
    invitations,  // صفيفة الدعوات المُحولة
    generate_pdf: true,
    generate_zip: true,
    upload_individual_barcodes: false,
    layout_config: { ...layout }
  }
)
```

---

## 6. ⚠️ الفجوات والمشاكل الحالية

### 1️⃣ عدم التحقق من الأعمدة الإضافية (Custom Fields)
**المشكلة:**
- لا يتم دعم استيراد الحقول المخصصة مثل:
  - رقم المقعد
  - رقم الطاولة
  - المنطقة (Zone)
  - قاعة الحفل
  - رقم الهاتف
  - البريد الإلكتروني

**المتوقع:**
- النموذج يدعم هذه الحقول في `GuestCreate` و `InvitationCreate`
- لكن الاستيراد من الإكسل **لا يقرأها**

### 2️⃣ لا توجد معلومات عن الأعمدة المتوقعة
**المشكلة:**
- النموذج المُحمل (`downloadExcelTemplate`) يعرض 3 أعمدة فقط:
  ```typescript
  const worksheet = XLSX.utils.json_to_sheet([
    { 'اسم الضيف': 'أحمد محمد', 'عدد الدعوات': 1, 'نوع التذكرة': 'normal' }
  ])
  ```
- لا تعليقات أو توثيق حول الأعمدة الاختيارية

### 3️⃣ الكشف المرن يقلل من حساسية الأخطاء
**المشكلة:**
- تقبل أسماء أعمدة متعددة قد يؤدي لالتباس
- مثلاً: `عدد الدعوات`, `invitation_count`, `count` كلها مقبولة
- إذا كتب المستخدم `عدد_الدعوات` (بدون مسافات) لن يتم التعرف عليها

### 4️⃣ لا توجد تحذيرات للقيم الافتراضية
**المشكلة:**
- إذا لم يحدد نوع التذكرة → **يُفترض تلقائياً `normal`** دون تنبيه للمستخدم
- إذا لم يحدد عدد الدعوات → **يُفترض `1`** دون تنبيه

### 5️⃣ حد أقصى 100 دعوة لكل ضيف
**المشكلة:**
- قد تكون محدودة جداً للحفلات الكبيرة

---

## 7. 📋 الأعمدة التي يجب أن تكون إلزامية (التوصية)

### ✅ إلزامي جداً (لا استبدال):
| العمود | السبب | مثال |
|------|------|-------|
| **اسم الضيف** | تعريف الضيف | "أحمد محمد العلي" |

### ⚠️ اختياري لكن مهم جداً:
| العمود | السبب | القيم المقبولة |
|------|------|------------|
| **عدد الدعوات** | لتكرار الدعوة | 1-100 |
| **نوع التذكرة** | تحديد الفئة | VIP, normal |

### 🔲 يجب إضافته (غير مدعوم حالياً):
| العمود | السبب | المثال |
|------|------|--------|
| **رقم الهاتف** | التواصل | 0501234567 |
| **البريد الإلكتروني** | الإرسال | test@example.com |
| **رقم المقعد** | الجلوس | A12, B5 |
| **قاعة الحفل** | الموقع | البهو الذهبي |
| **منطقة/منطقة** | القسم | الشرق، الغرب |
| **الشركة** | المعلومات الإضافية | شركة XYZ |
| **الوظيفة** | المعلومات الإضافية | مهندس |

---

## 8. 🎯 ملخص: ماذا يحدث عند الاستيراد

### في الحالة السعيدة:
```
1. المستخدم يختار ملف Excel
2. يُقرأ الملف (الورقة الأولى فقط)
3. يتم التحقق من:
   ✓ وجود اسم الضيف (إلزامي)
   ✓ عدد الدعوات بين 1-100 (اختياري، افتراضي: 1)
   ✓ نوع التذكرة (اختياري، افتراضي: normal)
4. يتم عرض معاينة في الواجهة (أول 5 صفوف)
5. يتم حساب الإجمالي
6. يتم التحقق من الحصص
7. يُنقر "بدء التوليد" → يتم إرسال الدعوات
```

### في حالة الأخطاء:
```
1. تُعرض رسائل خطأ محددة بالسطر
2. يتم عرض أول 5 أخطاء فقط
3. يتم عرض عدد الصفوف الصحيحة في الإحصائيات
4. زر "بدء التوليد" يبقى مُعطّلاً
5. يمكن المستخدم تحميل ملف جديد
```

---

## 9. 📌 ملاحظات إضافية مهمة

### بخصوص قاعدة البيانات:
- الضيوف (Guests) يُخزنون في جدول `guests` منفصل
- الدعوات (Invitations) يُخزنون في جدول `invitations`
- الاستيراد من الإكسل **لا ينشئ ضيوف** في جدول guests
- بدلاً من ذلك، يستخدم `guest_name` مباشرة في الدعوات

### بخصوص الأمان:
- لا يوجد تحقق من صيغة البريد الإلكتروني أو الهاتف
- لا يوجد التكشف عن التكرارات (duplicate names)
- لا يوجد حد أقصى لعدد الصفوف في الملف

### بخصوص الأداء:
- يتم قراءة الملف بالكامل في الذاكرة (arrayBuffer)
- لا توجد معالجة دفعية للملفات الكبيرة
- الملفات الضخمة قد تسبب تأخير الواجهة

---

## 10. 🔍 الملفات الرئيسية المعنية

```
Frontend:
├── EventBarcodesTab.tsx (سطر 142-190) → handleGuestFileSelected
│   └── parseTicketClass (سطر 136-140) → تحليل نوع التذكرة
│   └── downloadExcelTemplate (سطر 123-128) → تحميل النموذج
└── EventInvitationsTab.tsx → عرض القائمة

Backend:
├── routes/guests.py → import endpoint (لكن غير مستخدم حالياً للإكسل)
├── routes/digital_invitations.py → يستقبل الدعوات
├── models/guest.py → GuestCreate, GuestImport
└── models/invitation.py → InvitationCreate, QuickInviteCreate

Database:
├── guests table → guest_name, phone, email, custom_fields, etc
└── invitations table → guest_name, ticket_class, etc
```

---

## ملخص نهائي:

### ✅ يعمل حالياً:
- قراءة ملفات Excel (.xlsx, .xls)
- التحقق من اسم الضيف (إلزامي)
- التحقق من عدد الدعوات (1-100)
- تحليل نوع التذكرة (VIP/normal)
- عرض أخطاء واضحة بأرقام الصفوف
- معاينة البيانات
- التحقق من الحصص

### ❌ غير مدعوم:
- الحقول الإضافية (هاتف، بريد، مقعد، إلخ)
- التحقق من صيغة البيانات (email validation)
- كشف التكرارات
- معالجة الملفات الضخمة (streaming)
- توثيق واضح عن الأعمدة المتوقعة

### ⚠️ ينبغي التحذير عليها:
- الاعتماد على القيم الافتراضية (normal للتذكرة)
- تقبل أسماء أعمدة مختلفة قد يسبب التباس
- حد أقصى 100 دعوة لكل ضيف
- قراءة الورقة الأولى فقط من الملف
