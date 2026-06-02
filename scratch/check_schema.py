import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'invitations'"))
        for r in res.mappings().all():
            print(f"{r['column_name']}: {r['data_type']}")

if __name__ == '__main__':
    asyncio.run(check())
