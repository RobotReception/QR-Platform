"""Test actual rendering to verify names appear on image."""
import asyncio, sys, os
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services import render_service, batch_pipeline
import json

async def test_render():
    async with AsyncSessionLocal() as db:
        template_id = "eb830f2b-4001-4b1a-82ac-0aebae967d02"  # "اختبار الاسم" VIP

        # Load template, elements, background
        template = await batch_pipeline._load_template(db, template_id)
        elements = await batch_pipeline._load_template_elements(db, template_id)
        bg_bytes = await batch_pipeline._load_background(template)

        canvas_w = template.get("width_px", 1240)
        canvas_h = template.get("height_px", 1754)
        background_transform = batch_pipeline._extract_background_transform(template)

        print(f"Canvas: {canvas_w} x {canvas_h}")
        print(f"Background: {len(bg_bytes) if bg_bytes else 0} bytes")
        print(f"Elements (raw): {len(elements)}")

        # Expand slots
        render_elements = batch_pipeline._expand_repeated_sheet_slots(elements)
        print(f"Elements (expanded): {len(render_elements)}")

        for i, e in enumerate(render_elements):
            etype = e.get("element_type", "")
            dk = e.get("data_key", "")
            si = e.get("slot_index")
            x = float(e.get("x", 0))
            y = float(e.get("y", 0))
            print(f"  [{i}] {etype:15s} dk={dk!s:25s} slot={si} pos=({x:.3f},{y:.3f})")

        # Build 4 different contexts (simulating 4 guests)
        names = ["الشيخ محمد بن عبدالله", "المهندس أحمد الشمري", "الدكتورة سارة العتيبي", "فهد القحطاني"]
        slot_contexts = []
        for name in names:
            ctx = {
                "guest": {"name": name, "name_ar": name},
                "event": {"title": "حفل تخرج", "date": "2025-06-28", "time": "19:00", "location": "فندق"},
                "invite": {"code": "ABC123", "barcode_payload": f"QENTRY-{name[:5]}", "token": "test-token"},
                "custom": {},
            }
            slot_contexts.append(ctx)

        context = slot_contexts[0]

        print(f"\nRendering with {len(slot_contexts)} slot_contexts...")
        print(f"  context[0] guest.name = {slot_contexts[0]['guest']['name']}")
        print(f"  context[1] guest.name = {slot_contexts[1]['guest']['name']}")
        print(f"  context[2] guest.name = {slot_contexts[2]['guest']['name']}")
        print(f"  context[3] guest.name = {slot_contexts[3]['guest']['name']}")

        # Prepare base canvas
        base_canvas = render_service.prepare_background_canvas(
            bg_bytes, canvas_w, canvas_h, background_transform
        )

        # Render
        img_bytes = render_service.render_invitation_image(
            background_bytes=bg_bytes,
            elements=render_elements,
            context=context,
            slot_contexts=slot_contexts,
            canvas_width=canvas_w,
            canvas_height=canvas_h,
            background_transform=background_transform,
            base_canvas=base_canvas,
        )

        # Save to file for inspection
        out_path = os.path.join("scratch", "test_render_output.png")
        with open(out_path, "wb") as f:
            f.write(img_bytes)
        print(f"\nRendered image saved to: {out_path}")
        print(f"Image size: {len(img_bytes)} bytes")
        print("Open this file to verify names appear!")

asyncio.run(test_render())
