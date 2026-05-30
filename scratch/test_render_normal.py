"""
Test render with NORMAL template (8957476d) - the one with 4 QR codes already placed.
This template has the slot_index bug where all dynamic_text share the same slot_index.
"""
import asyncio, sys, os
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')

from app.database import AsyncSessionLocal
from app.services import render_service, batch_pipeline

async def test():
    async with AsyncSessionLocal() as db:
        template_id = "8957476d-931e-45db-a4ae-95973ad0c10c"  # NORMAL template

        template = await batch_pipeline._load_template(db, template_id)
        elements = await batch_pipeline._load_template_elements(db, template_id)
        bg_bytes = await batch_pipeline._load_background(template)

        canvas_w = template.get("width_px", 1240)
        canvas_h = template.get("height_px", 1754)
        print(f"Canvas: {canvas_w}x{canvas_h}")

        background_transform = batch_pipeline._extract_background_transform(template)

        print("\n=== BEFORE auto-assign ===")
        for i, e in enumerate(elements):
            if e.get("element_type") in ("dynamic_text", "guest_name"):
                dk = e.get("data_key", "")
                si = e.get("slot_index")
                x = float(e.get("x", 0))
                y = float(e.get("y", 0))
                print(f"  [{i}] slot={si} dk={dk:20s} pos=({x:.3f},{y:.3f})")

        expanded = batch_pipeline._expand_repeated_sheet_slots(elements)
        final = batch_pipeline._auto_assign_slot_indices(expanded)

        print("\n=== AFTER auto-assign ===")
        for i, e in enumerate(final):
            if e.get("element_type") in ("dynamic_text", "guest_name"):
                dk = e.get("data_key", "")
                si = e.get("slot_index")
                x = float(e.get("x", 0))
                y = float(e.get("y", 0))
                fs = e.get("font_size", 0)
                print(f"  [{i}] slot={si} dk={dk:20s} pos=({x:.3f},{y:.3f}) font={fs}")

        # 4 different names for 4 slots
        names = ["عبدالرحمن الدوسري", "خالد المالكي", "نورة الحربي", "سلطان العنزي"]
        jobs = ["مدير المبيعات", "محاسب", "مصممة", "مهندس برمجيات"]
        companies = ["شركة النور للتجارة", "مؤسسة الأمان", "استوديو إبداع", "تقنية المستقبل"]

        slot_contexts = []
        for i in range(4):
            slot_contexts.append({
                "guest": {"name": names[i], "name_ar": names[i]},
                "event": {"title": "مؤتمر التحول الرقمي", "date": "2025-06-28", "time": "19:00"},
                "invite": {"code": f"NORMAL{i}", "barcode_payload": f"QENTRY-NORMAL-{i}", "token": f"tok{i}"},
                "custom": {"المسمى الوظيفي": jobs[i], "الجهة": companies[i]},
            })

        base_canvas = render_service.prepare_background_canvas(
            bg_bytes, canvas_w, canvas_h, background_transform
        )

        img_bytes = render_service.render_invitation_image(
            background_bytes=bg_bytes,
            elements=final,
            context=slot_contexts[0],
            slot_contexts=slot_contexts,
            canvas_width=canvas_w,
            canvas_height=canvas_h,
            background_transform=background_transform,
            base_canvas=base_canvas,
        )

        output_path = os.path.join("scratch", "test_render_normal.png")
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        print(f"\nRendered image saved to: {output_path}")
        print(f"Image size: {len(img_bytes)} bytes")

asyncio.run(test())
