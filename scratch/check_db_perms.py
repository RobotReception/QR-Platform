import sys
sys.path.insert(0, 'd:/QR')
import asyncio
from app.database import get_db
from sqlalchemy import text

async def f():
    async for db in get_db():
        r = await db.execute(text("SELECT key FROM permissions ORDER BY key"))
        for row in r.fetchall():
            print(row[0])
        break

if __name__ == "__main__":
    asyncio.run(f())
