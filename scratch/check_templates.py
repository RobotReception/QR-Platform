import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, name, ticket_class, template_type, event_id FROM invite_templates"))
        for row in res.mappings():
            ascii_name = row['name'].encode('ascii', 'backslashreplace').decode('ascii')
            print(f"Template id={row['id']} name={ascii_name} ticket_class={row['ticket_class']}")
            
            res2 = await conn.execute(text("SELECT id, element_type, data_key FROM template_elements WHERE template_id = :tid"), {'tid': row['id']})
            for row2 in res2.mappings():
                print(f"  Element id={row2['id']} type={row2['element_type']} data_key={row2['data_key']}")

asyncio.run(main())
