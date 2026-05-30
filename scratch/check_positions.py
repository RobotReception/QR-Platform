import asyncio, sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        # Get the latest designed template
        r = await db.execute(text(
            "SELECT id, name, width_px, height_px FROM invite_templates "
            "WHERE template_type='designed' ORDER BY updated_at DESC LIMIT 1"
        ))
        tmpl = r.mappings().first()
        if not tmpl:
            print("No designed template found")
            return

        tid = tmpl["id"]
        tname = tmpl["name"]
        cw = int(tmpl["width_px"] or 1240)
        ch = int(tmpl["height_px"] or 1754)
        print(f"Template: {tname}")
        print(f"Template ID: {tid}")
        print(f"Canvas: {cw} x {ch}")
        print()

        # Get elements
        r2 = await db.execute(text(
            "SELECT element_type, data_key, x, y, width, height, font_size "
            "FROM template_elements WHERE template_id = :tid ORDER BY sort_order"
        ), {"tid": tid})

        print(f"  {'Type':15s} {'data_key':15s} | {'x':>7s} {'y':>7s} {'w':>7s} {'h':>7s} | {'left':>5s} {'top':>5s} {'wpx':>5s} {'hpx':>5s} | font")
        print("  " + "-" * 95)
        for e in r2.mappings().all():
            etype = e["element_type"]
            dk = str(e["data_key"] or "")
            x = float(e["x"]); y = float(e["y"])
            w = float(e["width"]); h = float(e["height"])
            fs = float(e["font_size"] or 0)
            lpx = round(x * cw); tpx = round(y * ch)
            wpx = round(w * cw); hpx = round(h * ch)
            print(f"  {etype:15s} {dk:15s} | {x:7.4f} {y:7.4f} {w:7.4f} {h:7.4f} | {lpx:5d} {tpx:5d} {wpx:5d} {hpx:5d} | {fs:.0f}px")

asyncio.run(check())
