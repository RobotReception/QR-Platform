import asyncio, sys, os
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')

from app.database import AsyncSessionLocal
from app.services import render_service, batch_pipeline

async def render_test():
    async with AsyncSessionLocal() as db:
        template_id = "ae184d33-567c-40e5-a8d4-dfe7aeea5cbd"

        template = await batch_pipeline._load_template(db, template_id)
        elements = await batch_pipeline._load_template_elements(db, template_id)
        bg_bytes = await batch_pipeline._load_background(template)

        canvas_w = template.get("width_px", 1240)
        canvas_h = template.get("height_px", 1754)
        print(f"Canvas: {canvas_w}x{canvas_h}")

        background_transform = batch_pipeline._extract_background_transform(template)
        
        # Build 4 fake slot_contexts
        slot_contexts = []
        for i in range(4):
            slot_contexts.append({
                "guest": {"name": f"ضيف {i+1}", "name_ar": f"ضيف {i+1}"},
                "event": {"title": "حفل تخرج 2025", "date": "2025-06-28", "time": "19:00"},
                "invite": {"code": f"CODE{i+1}", "barcode_payload": f"https://example.com/i/token{i+1}", "token": f"token{i+1}"},
                "custom": {},
            })

        base_canvas = render_service.prepare_background_canvas(
            bg_bytes, canvas_w, canvas_h, background_transform
        )

        img_bytes = render_service.render_invitation_image(
            background_bytes=bg_bytes,
            elements=elements,
            context=slot_contexts[0],
            slot_contexts=slot_contexts,
            canvas_width=canvas_w,
            canvas_height=canvas_h,
            background_transform=background_transform,
            base_canvas=base_canvas,
        )

        output_path = os.path.join("scratch", "test_render_alignment_output.png")
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        print(f"Rendered image saved to: {output_path}")

asyncio.run(render_test())
