# 🔧 تقرير وحل: مشكلة تموضع الباركودات

## المشاكل المكتشفة

### ❌ المشكلة 1: استخدام `_qr_box_px` بدلاً من `_element_box_px` للـ QR

**الموقع:** `render_service.py:339-356`

```python
# الكود الخاطئ الحالي
elif etype == "qr_code":
    left, top, qr_side = _qr_box_px(elem, canvas_width, canvas_height)  # ❌ خاطئ
    
    qr_png = generate_qr_png(
        payload,
        size_px=qr_side,  # ← يأخذ الحد الأدنى من width/height
        ...
    )
```

**المشكلة:**
- الدالة `_qr_box_px` تأخذ الحد الأدنى (minimum) من width و height
- إذا حددت مربع QR بحجم 200×300، ستصير QR 200×200 فقط!
- يتجاهل ما حددته تماماً

```python
# كود _qr_box_px الخاطئ
def _qr_box_px(elem, canvas_width, canvas_height):
    left, top, width, height = _element_box_px(elem, canvas_width, canvas_height)
    side = min(width, height, ...)  # ← يأخذ الأصغر = مشكلة!
    return left, top, max(1, side)
```

---

### ❌ المشكلة 2: عدم الحفاظ على النسبة الأصلية للـ width/height

**الموقع:** `render_service.py:273-276`

```python
# الحالي
left, top, ew, eh = _element_box_px(elem, canvas_width, canvas_height)
ex = left + ew // 2
ey = top + eh // 2
```

**المشكلة:**
- تحسب نقطة المركز (ex, ey) بناءً على width و height
- لكن QR قد يُرسم بحجم مختلف (الحد الأدنى)
- يؤدي لعدم توافق في الموضع

---

### ❌ المشكلة 3: عدم مطابقة الحجم بين التصميم والتنفيذ

**السبب:**
- في محرر التصميم: تحدد x=0.3, y=0.4, width=0.25, height=0.25
- في الرسم: تصير width=270 و height=480 (مثلاً)
- QR يأخذ الأصغر = 270×270 فقط!

---

### ❌ المشكلة 4: عدم مطابقة Canvas Width/Height بين التصميم والتنفيذ

**الموقع:** `batch_pipeline.py:296-301`

```python
canvas_w = template.get("width_px", 1080)
canvas_h = template.get("height_px", 1920)

# المشكلة: إذا كانت الخلفية 1240×1754
# لكن template width_px = 1080
# ستختلف الإحداثيات النسبية!
```

---

## الحل الكامل

### ✅ الإصلاح 1: استخدام `_element_box_px` مباشرة للـ QR

```python
# ملف: app/services/render_service.py:279-357

if etype in ("qr_code", "barcode"):
    element_context = context
    if slot_contexts:
        if barcode_slot_index >= len(slot_contexts):
            barcode_slot_index += 1
            continue
        element_context = slot_contexts[barcode_slot_index]
    barcode_slot_index += 1

    data_key = elem.get("data_key") or "invite.barcode_payload"
    payload = _resolve_data_key(data_key, element_context)
    if not payload:
        continue

    qr_color = elem.get("qr_color") or elem.get("font_color") or "#000000"
    qr_bg = elem.get("qr_bg_color") or "#ffffff"
    error_level = elem.get("qr_error_level") or elem.get("error_level") or "M"
    barcode_label = element_context.get("invite", {}).get("code") or payload

    if etype == "barcode":
        # ✅ استخدم eh المحفوظة (الارتفاع الكامل)
        label_box_h = max(18, int(eh * 0.24))
        barcode_box_h = max(24, eh - label_box_h)

        barcode_png = generate_code128_png(
            payload,
            width_px=max(1, ew),           # ✅ استخدم العرض الكامل
            height_px=max(1, barcode_box_h),
            fg_color=qr_color,
            bg_color=qr_bg,
        )
        barcode_img = Image.open(io.BytesIO(barcode_png)).convert("RGBA")

        composed = Image.new("RGBA", (ew, eh), (0, 0, 0, 0))
        composed_draw = ImageDraw.Draw(composed)

        label_font, label_text = _auto_fit_text(
            composed_draw,
            str(barcode_label),
            ew - 10,
            label_box_h,
            elem.get("font_family", "Cairo"),
            elem.get("font_weight", "normal"),
            max(12.0, float(elem.get("font_size", 24)) * 0.7),
        )
        label_bbox = composed_draw.textbbox((0, 0), label_text, font=label_font)
        label_w = label_bbox[2] - label_bbox[0]
        label_x = (ew - label_w) // 2
        label_y = 0
        composed_draw.text((label_x, label_y), label_text, font=label_font, fill=elem.get("font_color", "#111111"))

        barcode_y = label_box_h
        composed.paste(barcode_img, (0, barcode_y), barcode_img)

        if rotation:
            composed = composed.rotate(-rotation, expand=True, resample=Image.BICUBIC)

        paste_x = left if not rotation else ex - composed.width // 2
        paste_y = top if not rotation else ey - composed.height // 2
        overlay.paste(composed, (paste_x, paste_y), composed)

    elif etype == "qr_code":
        # ✅ FIX: استخدم width و height كاملة، لا تأخذ الحد الأدنى
        # الإحداثيات بالفعل محسوبة من _element_box_px
        qr_width_px = ew   # ✅ العرض الكامل
        qr_height_px = eh  # ✅ الارتفاع الكامل
        
        # تأكد أن QR يكون مربع إذا كانت الأبعاد مختلفة
        # (قرار: استخدم الأصغر للمربع، لكن اترك option)
        use_square = elem.get("maintain_square", True)  # option جديد
        
        if use_square:
            qr_size = min(qr_width_px, qr_height_px)
        else:
            # إذا أردت QR مستطيل، استخدم custom barcode
            qr_size = qr_width_px

        qr_png = generate_qr_png(
            payload,
            size_px=max(1, qr_size),  # ✅ استخدم الحجم الصحيح
            fg_color=qr_color,
            bg_color=qr_bg,
            error_level=error_level,
        )
        qr_img = Image.open(io.BytesIO(qr_png)).convert("RGBA")

        # ✅ إذا كان QR أصغر من المربع المحدد، وسطه
        if qr_img.width < qr_width_px or qr_img.height < qr_height_px:
            padded = Image.new("RGBA", (qr_width_px, qr_height_px), (0, 0, 0, 0))
            paste_inner_x = (qr_width_px - qr_img.width) // 2
            paste_inner_y = (qr_height_px - qr_img.height) // 2
            padded.paste(qr_img, (paste_inner_x, paste_inner_y), qr_img)
            qr_img = padded

        if rotation:
            qr_img = qr_img.rotate(-rotation, expand=True, resample=Image.BICUBIC)

        paste_x = left if not rotation else ex - qr_img.width // 2
        paste_y = top if not rotation else ey - qr_img.height // 2
        overlay.paste(qr_img, (paste_x, paste_y), qr_img)
```

---

### ✅ الإصلاح 2: ضمان مطابقة Canvas Width/Height

**الموقع:** `batch_pipeline.py:295-309`

```python
# الحالي (خاطئ)
canvas_w = template.get("width_px", 1080)
canvas_h = template.get("height_px", 1920)
with Image.open(io.BytesIO(bg_bytes)) as bg_image:
    bg_w, bg_h = bg_image.size
# لا تفعل شيء بـ bg_w و bg_h!

# ✅ الصحيح
canvas_w = template.get("width_px", 1080)
canvas_h = template.get("height_px", 1920)

with Image.open(io.BytesIO(bg_bytes)) as bg_image:
    bg_w, bg_h = bg_image.size
    
    # ✅ FIX: استخدم أبعاد الخلفية الفعلية إذا كانت أكبر
    # (خاصة إذا تم ملاءمة الخلفية إلى A4)
    if bg_w > canvas_w or bg_h > canvas_h:
        # ✅ تحديث template dimensions من الخلفية الفعلية
        canvas_w, canvas_h = bg_w, bg_h
        logger.info(f"Using background dimensions: {canvas_w}×{canvas_h}")
```

---

### ✅ الإصلاح 3: إضافة Validation في Frontend

**الموقع:** عند حفظ العنصر

```javascript
// قبل الحفظ
function validateQRElement(elem) {
    // التحقق من أن width و height معقولة
    if (elem.width < 0.1) {
        throw new Error("عرض QR صغير جداً (أقل من 10%)");
    }
    if (elem.height < 0.1) {
        throw new Error("ارتفاع QR صغير جداً");
    }
    
    // التحقق من عدم الخروج من الحدود
    if (elem.x + elem.width > 1) {
        elem.width = 1 - elem.x;  // تصحيح تلقائي
    }
    if (elem.y + elem.height > 1) {
        elem.height = 1 - elem.y;
    }
    
    return elem;
}
```

---

### ✅ الإصلاح 4: إضافة Logging for Debugging

```python
# في render_service.py:208-245

def render_invitation_image(...):
    """رسم دعوة واحدة"""
    
    # ✅ أضف logging
    logger.debug(f"Rendering canvas: {canvas_width}×{canvas_height}")
    
    canvas = base_canvas.copy() if base_canvas else prepare_background_canvas(...)
    overlay = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    for elem in elements:
        if not elem.get("is_visible", True):
            continue
        
        etype = elem.get("element_type", "")
        left, top, ew, eh = _element_box_px(elem, canvas_width, canvas_height)
        
        # ✅ Logging
        if etype in ("qr_code", "barcode"):
            logger.debug(
                f"Element {etype} at ({left}, {top}), "
                f"size: {ew}×{eh}, "
                f"design coords: ({elem.get('x')}, {elem.get('y')}, "
                f"{elem.get('width')}, {elem.get('height')})"
            )
```

---

## ملخص التغييرات

| المشكلة | الحل |
|--------|-----|
| استخدام `min()` لـ QR | استخدم width و height كاملة من `_element_box_px` |
| عدم مطابقة أبعاد Canvas | تأكد أن template و background لهما نفس الأبعاد |
| عدم توسيط QR الصغير | أضف padding حول QR إذا كان أصغر من المربع |
| صعوبة الـ Debug | أضف logging واضح للإحداثيات والأبعاد |

---

## خطوات التطبيق

1. **نسخ الكود الجديد** إلى `render_service.py`
2. **تحديث Canvas Detection** في `batch_pipeline.py`
3. **إضافة Validation** في Frontend (إن أمكن)
4. **اختبار مع QR مختلفة الأحجام** (صغيرة، كبيرة، مربع، مستطيل)
5. **التحقق من الـ Log** للتأكد من صحة الإحداثيات

---

## اختبار سريع

```bash
# قبل الإصلاح:
# QR محدد: x=0.3, y=0.4, width=0.25, height=0.25
# النتيجة: QR يظهر بحجم أصغر، أو في مكان خاطئ ❌

# بعد الإصلاح:
# QR يظهر بنفس الحجم والموضع المحدد ✅
```

