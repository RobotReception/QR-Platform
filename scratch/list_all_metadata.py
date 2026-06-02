import asyncio
import json
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id, guest_name, metadata, rsvp_status, created_at FROM invitations ORDER BY created_at DESC LIMIT 15"))
        rows = res.mappings().all()
        print(f"Total invitations: {len(rows)}")
        for r in rows:
            meta = r['metadata'] or {}
            print(json.dumps({
                "id": str(r['id']),
                "name": r['guest_name'],
                "rsvp_status": r['rsvp_status'],
                "created_at": str(r['created_at']),
                "metadata": meta
            }, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(check())
