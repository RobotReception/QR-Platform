import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        res = await conn.execute(
            text("UPDATE profiles SET is_staff = true WHERE id = :uid"),
            {"uid": "9d32fe8c-50a6-4bc0-9b0b-278bdde11109"}
        )
        print(f"Updated profiles table. Rows affected: {res.rowcount}")

asyncio.run(main())
