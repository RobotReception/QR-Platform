import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath("."))

from app.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    db = AsyncSessionLocal()
    try:
        res = await db.execute(text("SELECT id, name, slug FROM tenants LIMIT 1"))
        row = res.first()
        if row:
            print(f"TENANT_ID: {row[0]}")
            print(f"NAME: {row[1]}")
            print(f"SLUG: {row[2]}")
        else:
            print("NO_TENANT_FOUND")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
