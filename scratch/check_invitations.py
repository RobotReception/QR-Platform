import asyncio
import json
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT id, guest_name, ticket_class, status, rsvp_status, metadata FROM invitations ORDER BY created_at DESC LIMIT 20"))
        rows = result.mappings().all()
        for r in rows:
            meta = r['metadata'] or {}
            # Print as JSON dump to avoid encoding errors in CP1252 terminal
            print(json.dumps({
                "id": str(r['id']),
                "guest_name": r['guest_name'],
                "status": r['status'],
                "rsvp_status": r['rsvp_status'],
                "metadata": meta
            }, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(check())
