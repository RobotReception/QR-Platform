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
        try:
            res = await conn.execute(text("SELECT id, email, raw_user_meta_data FROM auth.users"))
            print("AUTH USERS IN DATABASE:")
            for row in res.mappings():
                print(f"- ID: {row['id']}, Email: {row['email']}, Metadata: {row['raw_user_meta_data']}")
        except Exception as e:
            print("Could not query auth.users:", e)

asyncio.run(main())
