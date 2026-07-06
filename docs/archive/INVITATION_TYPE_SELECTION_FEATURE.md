# 🎯 ميزة اختيار نوع الدعوات (VIP/Normal)

**التاريخ:** 18 مايو 2026  
**الإصدار:** 4.3.0  
**الحالة:** ✅ **تم التنفيذ**

---

## 🎬 الميزة الجديدة

### نظام متكامل لاختيار نوع الدعوات

```
✅ اختيار نوع الدعوات أولاً (خطوة 1)
✅ تصفية القوالب حسب النوع (خطوة 2)
✅ تحميل ملف Excel (خطوة 3)
✅ تعيين البيانات (خطوة 4)
✅ معاينة النتائج مع النوع (خطوة 5)
```

---

## 🎨 الخطوات الجديدة

### خطوة 1️⃣: اختيار نوع الدعوات (جديدة)

```
┌─────────────────────────────────────┐
│ اختر نوع الدعوات                   │
│                                     │
│ ┌──────────────┐  ┌──────────────┐ │
│ │ 👑 VIP       │  │ 👥 عادي      │ │
│ │ دعوات فاخرة  │  │ دعوات عادية  │ │
│ │ مميزة        │  │ للضيوف      │ │
│ └──────────────┘  └──────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

#### المميزات:
- 🎨 تصميم جميل مع أيقونات واضحة
- ✨ رسوم متحركة احترافية
- 📱 responsive design
- ⚡ انتقالات سلسة

---

### خطوة 2️⃣: اختيار القالب (محسّنة)

```
بعد اختيار النوع:
  ↓
تصفية القوالب تلقائياً
  ├─ عرض قوالب VIP فقط (إذا اختار VIP)
  └─ عرض قوالب Normal فقط (إذا اختار Normal)
  ↓
اختيار قالب من القائمة المصفاة
```

#### تصفية القوالب:

```typescript
// تصفية بناءً على النوع
const templates = invitationType
  ? allTemplates.filter((t) => t.type === invitationType || !t.type)
  : []
```

---

### خطوة 3️⃣: تحميل الملف (بدون تغيير)

```
تحميل ملف Excel
  ↓
استخراج الأعمدة تلقائياً
```

---

### خطوة 4️⃣: تعيين البيانات (بدون تغيير)

```
تعيين الأعمدة
  ├─ اسم الضيف
  ├─ التاريخ
  ├─ الوقت
  └─ رقم المقعد
```

---

### خطوة 5️⃣: معاينة النتائج (محسّنة)

```
┌──────────────────────────────────────┐
│ معاينة النتائج                      │
│                                      │
│ القالب: Template Name               │
│ النوع: 👑 VIP                       │
│ عدد الضيوف: 25                      │
│                                      │
│ ┌────────────────────────────────┐  │
│ │ اسم    │ التاريخ │ الوقت│ المقعد│  │
│ ├────────────────────────────────┤  │
│ │ أحمد   │ 2025    │ 19:00│ A12   │  │
│ │ فاطمة  │ 2025    │ 19:00│ B5    │  │
│ │ عمر    │ 2025    │ 19:00│ C8    │  │
│ └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

#### المعلومات المعروضة:
- ✓ القالب المختار
- ✓ **نوع الدعوات** (VIP/Normal)
- ✓ عدد الضيوف
- ✓ البيانات المعاينة

---

## 📊 الخطوات الكاملة

```
Start
  ↓
[1] 👑/👥 اختيار النوع
    ├─ VIP   → قوالب VIP
    └─ Normal → قوالب عادية
  ↓
[2] 🎨 اختيار القالب (مصفى)
  ↓
[3] 📄 تحميل الملف
  ↓
[4] 🔗 تعيين البيانات
  ↓
[5] 👁️ معاينة (مع النوع)
  ↓
✅ إنشاء الدعوات
```

---

## 🔧 التطبيق العملي

### Frontend - React Component

```typescript
// المكون الرئيسي يستقبل نوع الدعوات
interface TemplateSelectionFlowProps {
  eventId: string
  onComplete: (data: {
    invitationType: 'vip' | 'normal'  // ← جديد
    templateId: string
    templateName: string
    guests: Guest[]
    columnMapping: Record<string, string>
  }) => void
  onCancel: () => void
}

// تصفية القوالب بناءً على النوع
const templates = invitationType
  ? allTemplates.filter((t) => t.type === invitationType || !t.type)
  : []

// إرسال النوع عند الإنشاء
const handleComplete = () => {
  onComplete({
    invitationType,  // ← إرسال النوع
    templateId: selectedTemplateId,
    templateName: selectedTemplateName,
    guests,
    columnMapping,
  })
}
```

### Backend - Database

```python
# في جدول الدعوات
class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    template_id = db.Column(db.Integer, db.ForeignKey('template.id'))
    
    # حقل جديد لنوع الدعوات
    invitation_type = db.Column(
        db.Enum('vip', 'normal'),
        default='normal'
    )
    
    guest_name = db.Column(db.String(255))
    event_date = db.Column(db.Date)
    event_time = db.Column(db.Time)
    seat_number = db.Column(db.String(50))
    barcode = db.Column(db.String(255), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# في جدول القوالب
class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    name = db.Column(db.String(255))
    
    # حقل جديد لتصنيف النوع
    type = db.Column(
        db.Enum('vip', 'normal'),
        nullable=True  # nullable للقوالس العامة
    )
    
    background_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### API Endpoint

```python
# إنشاء دعوات جديدة مع النوع
@app.route('/api/events/<event_id>/invitations', methods=['POST'])
def create_invitations(event_id):
    data = request.json
    
    invitation_type = data.get('invitationType')  # ← النوع
    template_id = data.get('templateId')
    guests = data.get('guests', [])
    
    # التحقق من النوع
    if invitation_type not in ['vip', 'normal']:
        return {'error': 'Invalid invitation type'}, 400
    
    # التحقق من أن القالب يطابق النوع
    template = Template.query.get(template_id)
    if template.type and template.type != invitation_type:
        return {'error': 'Template type does not match invitation type'}, 400
    
    # إنشاء الدعوات
    invitations = []
    for guest in guests:
        invitation = Invitation(
            event_id=event_id,
            template_id=template_id,
            invitation_type=invitation_type,  # ← حفظ النوع
            guest_name=guest['guest_name'],
            event_date=guest['event_date'],
            event_time=guest['event_time'],
            seat_number=guest['seat_number'],
            barcode=generate_barcode()
        )
        invitations.append(invitation)
    
    db.session.add_all(invitations)
    db.session.commit()
    
    return {
        'message': f'Created {len(invitations)} {invitation_type} invitations',
        'count': len(invitations)
    }, 201

# الاستعلام عن الدعوات حسب النوع
@app.route('/api/events/<event_id>/invitations', methods=['GET'])
def get_invitations(event_id):
    invitation_type = request.args.get('type')  # ?type=vip
    
    query = Invitation.query.filter_by(event_id=event_id)
    if invitation_type:
        query = query.filter_by(invitation_type=invitation_type)
    
    invitations = query.all()
    return {
        'invitations': [{
            'id': inv.id,
            'guest_name': inv.guest_name,
            'type': inv.invitation_type,
            'barcode': inv.barcode
        } for inv in invitations]
    }, 200
```

---

## 🎨 الرسوم المتحركة

### دخول بطاقات النوع

```
Card 1 (VIP):  fadeInUp 0.5s delay 0.3s
Card 2 (Normal): fadeInUp 0.5s delay 0.4s
```

### عند التحديد

```
scaleIn 0.3s مع تغيير لون الحد والخلفية
```

### عند المرور

```
translateY(-8px) مع زيادة الظل
```

---

## ✅ الحالة الحالية

### تم تنفيذه ✅

- [x] نموذج React جديد مع 5 خطوات
- [x] خطوة اختيار النوع (جديدة)
- [x] تصفية القوالب حسب النوع
- [x] أنماط CSS احترافية
- [x] رسوم متحركة سلسة
- [x] معاينة مع النوع
- [x] توثيق شامل

### جاهز للدمج

```
✅ Frontend: TemplateSelectionFlow_V2.tsx
✅ CSS: invitation-type-selection.css
✅ Backend: API endpoint محسّن
✅ Database: حقول جديدة في الجداول
```

---

## 🚀 كيفية الاستخدام

### للمستخدمين

```
1. افتح نموذج إنشاء الدعوات
2. اختر نوع الدعوات (VIP أو Normal)
3. اختر قالب (مصفى تلقائياً)
4. حمّل ملف Excel
5. تحقق من البيانات
6. أنشئ الدعوات
```

### للمطورين

```typescript
// استبدل TemplateSelectionFlow.tsx
// ب TemplateSelectionFlow_V2.tsx

import { TemplateSelectionFlow } from './TemplateSelectionFlow_V2'

// يستقبل الآن invitationType في البيانات المعادة
const handleComplete = (data) => {
  console.log(data.invitationType) // 'vip' أو 'normal'
  // معالجة البيانات مع النوع
}
```

---

## 📊 مثال عملي

### السيناريو: إنشاء دعوات مختلطة

```
الخطوة 1: اختيار VIP
  ↓
الخطوة 2: اختيار قالب فاخر (VIP فقط)
  ↓
الخطوة 3-5: إنشاء 50 دعوة VIP

ثم:

الخطوة 1: اختيار Normal
  ↓
الخطوة 2: اختيار قالب عادي (Normal فقط)
  ↓
الخطوة 3-5: إنشاء 200 دعوة عادية

النتيجة: 50 VIP + 200 Normal = 250 دعوة كاملة
```

---

## 🎉 الفوائد

✅ **تنظيم أفضل** - دعوات منفصلة حسب النوع  
✅ **قوالب محددة** - كل نوع له قوالب خاصة  
✅ **إدارة سهلة** - تقارير منفصلة لكل نوع  
✅ **مرونة أكبر** - تخصيص كامل لكل نوع  
✅ **تجربة أفضل** - واجهة واضحة وسهلة  

---

**تم الإضافة في:** 18 مايو 2026  
**الإصدار:** 4.3.0  
**الحالة:** ✅ **جاهز للدمج**
