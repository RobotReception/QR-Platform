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
            text("SELECT id, template_id, status, count_total, created_at FROM generation_batches ORDER BY created_at DESC LIMIT 10")
        )
        print("Recent Batches:")
        for row in res.mappings():
            batch_id = row['id']
            tmpl_id = row['template_id']
            print(f"Batch ID: {batch_id} | Template ID: {tmpl_id} | Status: {row['status']} | Count: {row['count_total']}")
            
            # Print template elements count
            if tmpl_id:
                el_res = await conn.execute(
                    text("SELECT element_type, COUNT(*) as cnt FROM template_elements WHERE template_id = :tid GROUP BY element_type"),
                    {"tid": str(tmpl_id)}
                )
                print("  Template Elements:", list(el_res.mappings()))

asyncio.run(main())
