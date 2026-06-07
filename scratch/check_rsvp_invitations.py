import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        eid = "83cf6d0f-f89f-4bd2-86bd-3462171191b1"
        tid = "445a9aea-c4b4-458b-9105-db606b9c54a5"
        
        print("\n--- ALL INVITATIONS FOR AI EVENT ---")
        res = await conn.execute(text("""
            SELECT id, guest_name, pdf_url, zip_url, metadata, is_registration
            FROM invitations
            WHERE event_id = :eid AND tenant_id = :tid
        """), {"eid": eid, "tid": tid})
        for row in res.mappings():
            print(f"ID: {row['id']} | Name: {row['guest_name']} | PDF: {row['pdf_url'][:40] if row['pdf_url'] else 'None'} | RSVP: {row['metadata'].get('require_rsvp') if row['metadata'] else 'None'}")

asyncio.run(main())
