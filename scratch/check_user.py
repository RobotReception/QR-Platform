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
        res = await conn.execute(
            text("SELECT * FROM memberships WHERE tenant_id = '41006037-931e-4e1f-9a7f-964840982051'")
        )
        print("Rows for tenant 41006037-931e-4e1f-9a7f-964840982051:")
        for row in res.mappings():
            print(dict(row))

asyncio.run(main())
