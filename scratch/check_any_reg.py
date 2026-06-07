import asyncio
import json
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id, guest_name, is_registration, metadata, created_at FROM invitations ORDER BY created_at DESC LIMIT 5"))
        rows = res.mappings().all()
        for r in rows:
            print(json.dumps({
                "id": str(r['id']),
                "name": r['guest_name'],
                "is_registration": r['is_registration'],
                "metadata": r['metadata'],
                "created_at": str(r['created_at'])
            }, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(check())
