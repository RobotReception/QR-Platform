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
        # Find latest event in DB
        event_res = await conn.execute(text("SELECT id, title, tenant_id FROM events ORDER BY created_at DESC LIMIT 1"))
        event_row = event_res.mappings().first()
        if not event_row:
            print("No events found")
            return
        
        eid = str(event_row['id'])
        tid = str(event_row['tenant_id'])
        print(f"Latest Event: {event_row['title']} (ID: {eid}, Tenant: {tid})")

        # Get history
        print("\n--- GENERATION HISTORY ---")
        history_res = await conn.execute(text("""
            SELECT
                md5(COALESCE(pdf_url, '') || '|' || COALESCE(zip_url, '')) AS id,
                COUNT(*) AS total_invitations,
                COUNT(CASE WHEN ticket_class = 'vip' THEN 1 END) AS vip_count,
                COUNT(CASE WHEN ticket_class = 'normal' THEN 1 END) AS normal_count,
                MAX(updated_at) AS generated_at,
                pdf_url,
                zip_url
            FROM invitations
            WHERE event_id = :eid
              AND tenant_id = :tid
              AND (pdf_url IS NOT NULL OR zip_url IS NOT NULL)
              AND (metadata IS NULL OR metadata->>'generation_deleted' IS DISTINCT FROM 'true')
              AND is_registration = false
              AND (metadata IS NULL OR metadata->>'require_rsvp' IS DISTINCT FROM 'true')
            GROUP BY pdf_url, zip_url
            ORDER BY MAX(updated_at) DESC
            LIMIT 5
        """), {"eid": eid, "tid": tid})
        
        rows = list(history_res.mappings())
        for row in rows:
            print(f"Hash ID: {row['id']} | Total: {row['total_invitations']} | PDF: {row['pdf_url'][:60] if row['pdf_url'] else 'None'}")
            
            # Run details for this hash ID
            details_res = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM invitations
                WHERE event_id = :eid
                  AND tenant_id = :tid
                  AND md5(COALESCE(pdf_url, '') || '|' || COALESCE(zip_url, '')) = :opid
                  AND (metadata IS NULL OR metadata->>'generation_deleted' IS DISTINCT FROM 'true')
            """), {"eid": eid, "tid": tid, "opid": row['id']})
            details_row = details_res.mappings().first()
            print(f"  -> Detail query count: {details_row['count']}")

async def main_wrapper():
    try:
        await main()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main_wrapper())
