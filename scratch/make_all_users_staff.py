import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        res = await conn.execute(
            text("UPDATE profiles SET is_staff = true")
        )
        print(f"Updated profiles table. Rows affected: {res.rowcount}")

asyncio.run(main())
