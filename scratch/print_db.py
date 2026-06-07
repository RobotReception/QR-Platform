import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, name, ticket_class, template_type, event_id, tenant_id FROM invite_templates"))
        templates = []
        for row in res.mappings():
            templates.append({
                'id': str(row['id']),
                'name': row['name'],
                'ticket_class': row['ticket_class'],
                'template_type': row['template_type'],
                'event_id': str(row['event_id']) if row['event_id'] else None,
                'tenant_id': str(row['tenant_id'])
            })
        print(json.dumps(templates, ensure_ascii=False, indent=2))

asyncio.run(main())
