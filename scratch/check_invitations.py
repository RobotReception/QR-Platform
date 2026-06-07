import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        print("--- Checking invitations table columns ---")
        res = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'invitations'"))
        for row in res:
            print(f'{row[0]}: {row[1]}')
        
        print("\n--- Checking recent invitations data ---")
        data_res = await conn.execute(text("SELECT id, guest_name, rsvp_status, status, is_registration, created_at FROM invitations ORDER BY created_at DESC LIMIT 10"))
        for row in data_res.mappings().all():
            print(dict(row))

asyncio.run(main())
