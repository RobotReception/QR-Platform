import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, guest_name, guest_name_ar, ticket_class, metadata FROM invitations ORDER BY created_at DESC LIMIT 10"))
        rows = res.all()
        if not rows:
            print("No invitations found in database.")
            return
        for row in rows:
            inv_id, name, name_ar, t_class, meta = row
            print(f"\nID: {inv_id}")
            print(f"  guest_name: {repr(name)}")
            if name:
                for c in name:
                    print(f"    {repr(c)}: {hex(ord(c))}")
            print(f"  guest_name_ar: {repr(name_ar)}")
            if name_ar:
                for c in name_ar:
                    print(f"    {repr(c)}: {hex(ord(c))}")
            print(f"  metadata: {repr(meta)}")

asyncio.run(main())
