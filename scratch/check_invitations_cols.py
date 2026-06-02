import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        cols_res = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='invitations'"))
        cols = [dict(r) for r in cols_res.mappings().all()]
        print("Invitations Columns:")
        for c in cols:
            print(f"  {c['column_name']} ({c['data_type']})")

asyncio.run(main())
