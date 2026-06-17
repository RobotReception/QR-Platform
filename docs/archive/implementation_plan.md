# ربط النصوص الديناميكية بالباركودات — خطة التنفيذ

## المشكلة

عندما يحتوي القالب على أكثر من باركود (مثلاً 4 بطاقات على صفحة واحدة)، كل باركود يحصل على بيانات ضيف مختلف (**✅ يعمل**). لكن النصوص الديناميكية (`اسم الضيف`, `المسمى الوظيفي`, ...) تأخذ كلها بيانات **الضيف الأول فقط** (**❌ خطأ**).

## الحل: ربط عبر `slot_index`

كل باركود في القالب يمثل **Slot** (مكان لضيف). النصوص الديناميكية تُربط بنفس الـ Slot لتأخذ بيانات نفس الضيف.

```
Slot 0 (ضيف 1):  QR#0 + "اسم الضيف"#0 + "الجهة"#0
Slot 1 (ضيف 2):  QR#1 + "اسم الضيف"#1 + "الجهة"#1
Slot 2 (ضيف 3):  QR#2 + "اسم الضيف"#2 + "الجهة"#2
Slot 3 (ضيف 4):  QR#3 + "اسم الضيف"#3 + "الجهة"#3
```

---

## التغييرات المطلوبة

### Backend — render_service.py

#### [MODIFY] [render_service.py](file:///d:/QR/app/services/render_service.py)

تعديل معالجة `dynamic_text` و`guest_name` لاستخدام `slot_index`:

```diff
 elif etype == "dynamic_text":
     data_key = elem.get("data_key", "")
     if not data_key:
         continue
-    text = _resolve_data_key(data_key, context)
+    # Use slot_contexts if available and element has slot_index
+    slot_idx = elem.get("slot_index")
+    if slot_contexts and slot_idx is not None and 0 <= slot_idx < len(slot_contexts):
+        element_context = slot_contexts[slot_idx]
+    else:
+        element_context = context
+    text = _resolve_data_key(data_key, element_context)
     if not text:
-        text = context.get("custom", {}).get(data_key, "")
+        text = element_context.get("custom", {}).get(data_key, "")
```

نفس التعديل للعناصر legacy (سطر 410-415).

---

### Backend — نموذج قاعدة البيانات

#### [MODIFY] [models.py أو migration](file:///d:/QR/app/models.py)

إضافة عمود `slot_index` لجدول `template_elements`:

```sql
ALTER TABLE template_elements ADD COLUMN slot_index INTEGER DEFAULT NULL;
```

- `NULL` = يستخدم الـ context الأساسي (متوافق للخلف)
- `0, 1, 2, 3...` = يستخدم slot_contexts بنفس الترتيب

---

### Frontend — محرر التصميم

#### [MODIFY] [EventDesignEditorPage.tsx](file:///d:/QR/frontend/src/features/events/pages/EventDesignEditorPage.tsx)

في لوحة خصائص عنصر `dynamic_text`:
- إضافة حقل **"ربط بالباركود"** (dropdown)
- الخيارات: `تلقائي` / `باركود 1` / `باركود 2` / `باركود 3` / `باركود 4`
- عند الاختيار يُحفظ كـ `slot_index: 0 | 1 | 2 | 3`

**الربط التلقائي الذكي:** عند إضافة نص ديناميكي جديد:
- يبحث عن أقرب باركود بالمسافة (proximity)
- يُعين `slot_index` تلقائياً = ترتيب ذلك الباركود

---

### Frontend — API Types

#### [MODIFY] [templatesApi.ts](file:///d:/QR/frontend/src/features/events/api/templatesApi.ts)

```diff
 export interface TemplateElementRead {
   ...
+  slot_index: number | null
 }
 
 export interface TemplateElementCreateRequest {
   ...
+  slot_index?: number | null
 }
```

---

## التأثير على المستخدم

### قبل:
```
صفحة واحدة = 4 بطاقات
كل البطاقات تعرض: "الشيخ محمد بن عبدالله" (الضيف الأول فقط) ❌
```

### بعد:
```
صفحة واحدة = 4 بطاقات
بطاقة 1: "الشيخ محمد بن عبدالله" ✅
بطاقة 2: "المهندس أحمد الشمري" ✅
بطاقة 3: "الدكتورة سارة العتيبي" ✅
بطاقة 4: "عبدالرحمن الدوسري" ✅
```

---

## خطة التحقق

1. إنشاء قالب بـ 4 باركودات + 4 نصوص ديناميكية مربوطة
2. توليد دعوات من ملف Excel
3. التحقق من أن كل بطاقة تعرض بيانات ضيف مختلف
4. التحقق من التوافق مع القوالب القديمة (بدون slot_index)
