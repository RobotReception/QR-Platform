import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, tenant_id, event_id, ticket_class FROM invite_templates WHERE template_type = 'designed' ORDER BY created_at DESC LIMIT 5"))
        for tmpl in res.mappings():
            print(f"Template ID: {tmpl['id']} | Tenant ID: {tmpl['tenant_id']} | Event ID: {tmpl['event_id']} | Ticket Class: {tmpl['ticket_class']}")

asyncio.run(main())
