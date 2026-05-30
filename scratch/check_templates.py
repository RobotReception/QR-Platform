import asyncio, sys, os
sys.path.insert(0, ".")
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        r = await db.execute(text("""
            SELECT id, name, ticket_class, width_px, height_px
            FROM invite_templates 
            WHERE template_type = 'designed'
            ORDER BY created_at DESC LIMIT 10
        """))
        templates = [dict(row) for row in r.mappings().all()]
        print("=" * 80)
        print("DESIGNED TEMPLATES IN DATABASE")
        print("=" * 80)
        for t in templates:
            tid = str(t["id"])
            tc = str(t["ticket_class"] or "")
            nm = str(t["name"] or "")
            wp = t["width_px"]
            hp = t["height_px"]
            print(f"\n  [{tc}] {nm}")
            print(f"  Canvas: {wp} x {hp}")
            print(f"  ID: {tid}")
            
            er = await db.execute(text("""
                SELECT element_type, data_key, label, x, y, width, height, 
                       static_content, slot_index, is_visible, font_size
                FROM template_elements 
                WHERE template_id = :tid
                ORDER BY z_index, sort_order
            """), {"tid": tid})
            elements = [dict(row) for row in er.mappings().all()]
            if elements:
                print(f"  Elements ({len(elements)}):")
                for i, e in enumerate(elements):
                    etype = str(e["element_type"] or "")
                    dk = str(e["data_key"]) if e["data_key"] else "NULL"
                    lbl = str(e["label"] or "")
                    vis = e["is_visible"]
                    x = float(e["x"]) if e["x"] else 0
                    y = float(e["y"]) if e["y"] else 0
                    w = float(e["width"]) if e["width"] else 0
                    h = float(e["height"]) if e["height"] else 0
                    sc = str(e["static_content"]) if e["static_content"] else ""
                    si = e["slot_index"]
                    fs = e["font_size"]
                    print(f"    [{i}] type={etype} | data_key={dk} | label={lbl} | visible={vis}")
                    print(f"        pos=({x:.3f}, {y:.3f}) size=({w:.3f}, {h:.3f}) font={fs} slot={si}")
                    if sc:
                        print(f"        static_content={sc}")
            else:
                print("  *** NO ELEMENTS! ***")
            print("-" * 60)

asyncio.run(check())
