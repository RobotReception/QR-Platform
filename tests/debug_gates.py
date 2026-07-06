"""Debug: check event_gates table schema."""
import sys, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

import asyncio
from sqlalchemy import text

async def check():
    from app.database import get_db
    async for db in get_db():
        # Check event_gates columns
        r = await db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='event_gates'
            ORDER BY ordinal_position
        """))
        rows = r.fetchall()
        print("event_gates columns:")
        for row in rows:
            print(f"  {row[0]:25} {row[1]:20} nullable={row[2]}")
        break

asyncio.run(check())
