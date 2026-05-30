import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, name, width_px, height_px FROM invite_templates ORDER BY created_at DESC LIMIT 10"))
        for tmpl in res.mappings():
            print('Template:', tmpl)
            res2 = await conn.execute(text("SELECT element_type, width, height, x, y FROM template_elements WHERE template_id = :tid"), {'tid': tmpl['id']})
            for row in res2.mappings():
                print('  Element:', row)

asyncio.run(main())
