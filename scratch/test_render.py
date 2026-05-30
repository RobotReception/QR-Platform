"""
Full end-to-end test: renders a single card from the VIP template
with 4 slots to verify names appear correctly.
"""
import asyncio, sys, os, json
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services import render_service, batch_pipeline

async def test():
    async with AsyncSessionLocal() as db:
        template_id = "eb830f2b-4001-4b1a-82ac-0aebae967d02"

        template = await batch_pipeline._load_template(db, template_id)
        elements = await batch_pipeline._load_template_elements(db, template_id)
        bg_bytes = await batch_pipeline._load_background(template)

        canvas_w = template.get("width_px", 1240)
        canvas_h = template.get("height_px", 1754)
        print(f"Canvas: {canvas_w}x{canvas_h}")

        background_transform = batch_pipeline._extract_background_transform(template)
        expanded = batch_pipeline._expand_repeated_sheet_slots(elements)

        print(f"\nExpanded elements ({len(expanded)}):")
        for i, e in enumerate(expanded):
            etype = e.get("element_type", "")
            dk = e.get("data_key", "")
            si = e.get("slot_index")
            x = float(e.get("x", 0))
            y = float(e.get("y", 0))
            w = float(e.get("width", 0))
            h = float(e.get("height", 0))
            fs = e.get("font_size", 0)
            left = round(x * canvas_w)
            top = round(y * canvas_h)
            ew = round(w * canvas_w)
            eh = round(h * canvas_h)
            print(f"  [{i}] {etype:15s} slot={si} | rel=({x:.3f},{y:.3f},{w:.3f},{h:.3f}) | px=({left},{top},{ew},{eh}) | font={fs} | dk={dk}")

        # Build 4 fake slot_contexts (4 different names)
        names = ["الشيخ محمد بن عبدالله", "المهندس أحمد الشمري", "الدكتورة سارة العتيبي", "فهد القحطاني"]
        slot_contexts = []
        for name in names:
            slot_contexts.append({
                "guest": {"name": name, "name_ar": name},
                "event": {"title": "حفل تخرج 2025", "date": "2025-06-28", "time": "19:00"},
                "invite": {"code": "TEST1234", "barcode_payload": f"QENTRY-TEST-{name[:5]}", "token": "test123"},
                "custom": {},
            })

        base_canvas = render_service.prepare_background_canvas(
            bg_bytes, canvas_w, canvas_h, background_transform
        )

        img_bytes = render_service.render_invitation_image(
            background_bytes=bg_bytes,
            elements=expanded,
            context=slot_contexts[0],
            slot_contexts=slot_contexts,
            canvas_width=canvas_w,
            canvas_height=canvas_h,
            background_transform=background_transform,
            base_canvas=base_canvas,
        )

        output_path = os.path.join("scratch", "test_render_output.png")
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        print(f"\nRendered image saved to: {output_path}")
        print(f"Image size: {len(img_bytes)} bytes")

asyncio.run(test())
