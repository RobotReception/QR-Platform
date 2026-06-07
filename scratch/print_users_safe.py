import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, is_staff, full_name FROM profiles"))
        print("PROFILES IN DATABASE:")
        for row in res.mappings():
            # encode to avoid CP1252 errors
            name = row['full_name']
            print(f"- ID: {row['id']}, is_staff: {row['is_staff']}, name: {name}")

asyncio.run(main())
