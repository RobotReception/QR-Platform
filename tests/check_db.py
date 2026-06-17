import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'invite_templates'"))
        for row in res:
            print(f'{row[0]}: {row[1]}')
        
        # also print template_type enum if any
        try:
            res2 = await conn.execute(text("SELECT enum_range(NULL::template_type)"))
            print('template_type:', res2.scalar())
        except Exception as e:
            print('enum error:', e)

asyncio.run(main())
