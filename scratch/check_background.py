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
            text("SELECT id, name, background_url, width_px, height_px, ticket_class FROM invite_templates WHERE id = 'd606dcca-fb84-423e-b0b1-3df343a1a231'")
        )
        for row in res.mappings():
            print(dict(row))

asyncio.run(main())
