import asyncio, sys, os
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        # Get latest batches (without total_items)
        r = await db.execute(text("""
            SELECT gb.id, gb.event_id, gb.template_id, gb.mode, gb.status,
                   gb.progress, gb.error_message,
                   gb.metadata, gb.created_at,
                   t.name as template_name
            FROM generation_batches gb
            LEFT JOIN invite_templates t ON t.id = gb.template_id
            ORDER BY gb.created_at DESC LIMIT 5
        """))
        batches = [dict(row) for row in r.mappings().all()]
        print("=" * 80)
        print("RECENT BATCHES")
        print("=" * 80)
        for b in batches:
            print(f"\n  Batch: {b['id']}")
            print(f"  Template: {b['template_name']} (id={b['template_id']})")
            print(f"  Mode: {b['mode']} | Status: {b['status']} | Progress: {b['progress']}%")
            if b['error_message']:
                print(f"  ERROR: {b['error_message']}")
            print(f"  Metadata: {b['metadata']}")

            # Check invitations
            ir = await db.execute(text("""
                SELECT bi.invitation_id, bi.render_url, bi.render_status, bi.error_message,
                       i.guest_name, i.metadata as inv_metadata
                FROM batch_items bi
                JOIN invitations i ON i.id = bi.invitation_id
                WHERE bi.batch_id = :bid
                ORDER BY bi.created_at
                LIMIT 5
            """), {"bid": str(b["id"])})
            items = [dict(row) for row in ir.mappings().all()]
            if items:
                print(f"  Invitations:")
                for item in items:
                    gn = item.get("guest_name") or "NO_NAME"
                    rs = item.get("render_status") or "N/A"
                    err = item.get("error_message") or ""
                    inv_meta = item.get("inv_metadata")
                    if isinstance(inv_meta, str):
                        import json
                        try: inv_meta = json.loads(inv_meta)
                        except: inv_meta = {}
                    elif not isinstance(inv_meta, dict):
                        inv_meta = {}
                    cf = inv_meta.get("custom_fields", {})
                    print(f"    - guest_name={gn} | render={rs} | custom_fields={cf}")
                    if err:
                        print(f"      error: {err}")
            print("-" * 60)

asyncio.run(check())
