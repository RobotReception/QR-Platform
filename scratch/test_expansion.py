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
        batch_id = "aa794dc8-03e3-4629-9083-ce280b683997"      # latest batch

        # Load template
        template = await batch_pipeline._load_template(db, template_id)
        elements = await batch_pipeline._load_template_elements(db, template_id)
        
        print("=" * 80)
        print("TEMPLATE ELEMENTS (RAW from DB)")
        print("=" * 80)
        for i, e in enumerate(elements):
            etype = e.get("element_type", "")
            dk = e.get("data_key", "NULL")
            x = float(e.get("x", 0))
            y = float(e.get("y", 0))
            w = float(e.get("width", 0))
            h = float(e.get("height", 0))
            si = e.get("slot_index")
            print(f"  [{i}] {etype:15s} | data_key={dk!s:30s} | pos=({x:.3f},{y:.3f}) | size=({w:.3f},{h:.3f}) | slot={si}")

        # Now expand slots
        expanded = batch_pipeline._expand_repeated_sheet_slots(elements)
        print(f"\nAFTER _expand_repeated_sheet_slots() -> {len(expanded)} elements:")
        for i, e in enumerate(expanded):
            etype = e.get("element_type", "")
            dk = e.get("data_key", "NULL")
            x = float(e.get("x", 0))
            y = float(e.get("y", 0))
            w = float(e.get("width", 0))
            h = float(e.get("height", 0))
            si = e.get("slot_index")
            print(f"  [{i}] {etype:15s} | data_key={dk!s:30s} | pos=({x:.3f},{y:.3f}) | size=({w:.3f},{h:.3f}) | slot={si}")

        # How many barcode slots?
        bc_elements = batch_pipeline._barcode_elements(expanded)
        print(f"\nBarcode slots after expansion: {len(bc_elements)}")
        print(f"slots_per_card = {max(1, len(bc_elements))}")

        # Show what the grouping looks like
        print(f"\nThis means {len(bc_elements)} invitations are grouped per card/page!")
        print("But the dynamic_text element is only drawn ONCE at its original position!")
        print("\nTHIS IS THE BUG:")
        print("  - QR codes are duplicated to 4 positions by _expand_repeated_sheet_slots()")
        print("  - dynamic_text elements are NOT duplicated (they stay as non_slots)")
        print("  - So 4 QR codes show up but only 1 name in 1 position")

asyncio.run(test_render())
