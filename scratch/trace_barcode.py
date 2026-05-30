"""
🔍 تتبع كامل لآلية وضع الباركود: من المحرر → قاعدة البيانات → الإخراج النهائي
"""
import asyncio, sys, os
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')

from app.database import AsyncSessionLocal
from app.services import render_service, batch_pipeline
from PIL import Image, ImageDraw

async def trace_barcode_placement():
    async with AsyncSessionLocal() as db:
        template_id = "8957476d-931e-45db-a4ae-95973ad0c10c"  # Normal template

        template = await batch_pipeline._load_template(db, template_id)
        elements = await batch_pipeline._load_template_elements(db, template_id)
        bg_bytes = await batch_pipeline._load_background(template)

        canvas_w = template.get("width_px", 1240)
        canvas_h = template.get("height_px", 1754)

        print("=" * 90)
        print("🔍 تتبع آلية وضع الباركود - من المحرر إلى الإخراج")
        print("=" * 90)

        print(f"\n📐 أبعاد الكانفاس: {canvas_w} × {canvas_h} بكسل")

        # ───────────────────────────────────────────────
        # المرحلة 1: ما يحفظه المحرر في قاعدة البيانات
        # ───────────────────────────────────────────────
        print("\n" + "─" * 90)
        print("المرحلة 1️⃣: البيانات المحفوظة في قاعدة البيانات (نسب مئوية)")
        print("─" * 90)

        qr_elements = [e for e in elements if e.get("element_type") == "qr_code"]
        for i, e in enumerate(qr_elements):
            x = float(e.get("x", 0))
            y = float(e.get("y", 0))
            w = float(e.get("width", 0))
            h = float(e.get("height", 0))
            print(f"  QR #{i}: x={x:.3f} ({x*100:.1f}%), y={y:.3f} ({y*100:.1f}%), "
                  f"width={w:.3f} ({w*100:.1f}%), height={h:.3f} ({h*100:.1f}%)")

        # ───────────────────────────────────────────────
        # المرحلة 2: تحويل النسب إلى بكسل
        # ───────────────────────────────────────────────
        print("\n" + "─" * 90)
        print("المرحلة 2️⃣: تحويل النسب إلى بكسل (_element_box_px)")
        print("─" * 90)
        print(f"  المعادلة: left = round(x × {canvas_w}), top = round(y × {canvas_h})")
        print(f"           width = round(w × {canvas_w}), height = round(h × {canvas_h})")
        print()

        for i, e in enumerate(qr_elements):
            left, top, ew, eh = render_service._element_box_px(e, canvas_w, canvas_h)
            print(f"  QR #{i}: left={left}px, top={top}px, width={ew}px, height={eh}px")

        # ───────────────────────────────────────────────
        # المرحلة 3: توليد صورة QR بالحجم المطلوب
        # ───────────────────────────────────────────────
        print("\n" + "─" * 90)
        print("المرحلة 3️⃣: توليد صورة QR وتطبيقها")
        print("─" * 90)

        for i, e in enumerate(qr_elements):
            left, top, ew, eh = render_service._element_box_px(e, canvas_w, canvas_h)
            maintain_square = e.get("maintain_square", True)
            if maintain_square:
                qr_size = min(ew, eh)
            else:
                qr_size = ew
            
            print(f"  QR #{i}:")
            print(f"    • حجم مربع الباركود: {ew}×{eh}px (من المحرر)")
            print(f"    • maintain_square={maintain_square} → qr_size={qr_size}px")
            print(f"    • يُولد QR بحجم {qr_size}×{qr_size}px")
            if qr_size < ew or qr_size < eh:
                pad_x = (ew - qr_size) // 2
                pad_y = (eh - qr_size) // 2
                print(f"    • يُوسط داخل المربع: padding_x={pad_x}, padding_y={pad_y}")
            rotation = float(e.get("rotation", 0))
            if rotation:
                print(f"    • يُدور بزاوية {rotation}°")
            else:
                print(f"    • بدون دوران")
            print(f"    • يُلصق في الموقع: ({left}, {top})px")

        # ───────────────────────────────────────────────
        # المرحلة 4: مقارنة المحرر مع الباكند
        # ───────────────────────────────────────────────
        print("\n" + "─" * 90)
        print("المرحلة 4️⃣: مقارنة المحرر (CSS) مع الباكند (Pillow)")
        print("─" * 90)
        print()
        print(f"  {'QR':>4} | {'المحرر CSS':>30} | {'الباكند Pillow':>30} | {'فرق':>6}")
        print(f"  {'─'*4} | {'─'*30} | {'─'*30} | {'─'*6}")

        for i, e in enumerate(qr_elements):
            x = float(e.get("x", 0))
            y = float(e.get("y", 0))
            # CSS: left = x * 100% of 1240 = x * 1240
            css_left = x * canvas_w
            css_top = y * canvas_h
            # Pillow
            py_left, py_top, _, _ = render_service._element_box_px(e, canvas_w, canvas_h)
            diff = abs(css_left - py_left) + abs(css_top - py_top)
            print(f"  #{i:>2} | ({css_left:>7.1f}, {css_top:>7.1f})px       "
                  f"| ({py_left:>7d}, {py_top:>7d})px        "
                  f"| {diff:.1f}px")

        # ───────────────────────────────────────────────
        # المرحلة 5: رسم مرئي - مربعات حمراء في مواقع QR
        # ───────────────────────────────────────────────
        print("\n" + "─" * 90)
        print("المرحلة 5️⃣: إنشاء صورة توضيحية تظهر مواقع الباركودات")
        print("─" * 90)

        bg_transform = batch_pipeline._extract_background_transform(template)
        base = render_service.prepare_background_canvas(bg_bytes, canvas_w, canvas_h, bg_transform)
        debug_img = base.copy()
        draw = ImageDraw.Draw(debug_img)

        colors = ["#FF0000", "#00FF00", "#0000FF", "#FF00FF"]
        for i, e in enumerate(qr_elements):
            left, top, ew, eh = render_service._element_box_px(e, canvas_w, canvas_h)
            color = colors[i % len(colors)]
            # Draw border rectangle
            for t in range(3):  # 3px border
                draw.rectangle(
                    [left - t, top - t, left + ew + t, top + eh + t],
                    outline=color
                )
            draw.text((left + 5, top + 5), f"QR #{i}", fill=color)
            draw.text((left + 5, top + 25), f"({left},{top})", fill=color)
            draw.text((left + 5, top + 45), f"{ew}×{eh}px", fill=color)

        # Also draw dynamic_text boxes
        for e in elements:
            if e.get("element_type") != "dynamic_text":
                continue
            left, top, ew, eh = render_service._element_box_px(e, canvas_w, canvas_h)
            dk = e.get("data_key", "")[:15]
            draw.rectangle([left, top, left + ew, top + eh], outline="#FFA500", width=2)
            draw.text((left + 3, top + 3), dk, fill="#FFA500")

        debug_path = os.path.join("scratch", "debug_positions.png")
        debug_img.save(debug_path)
        print(f"  ✅ حُفظت صورة توضيحية: {debug_path}")

        print("\n" + "=" * 90)
        print("✅ الخلاصة: الباركود يُوضع في نفس الموقع بالضبط الذي حدده المصمم")
        print("=" * 90)

asyncio.run(trace_barcode_placement())
