import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.config import get_settings
from app.routes.fast_invitations import get_generation_operation_details, CurrentUser
from uuid import UUID
from fastapi import Request

class MockRequest:
    def __init__(self, tenant_id: str):
        self.headers = {"X-Tenant-ID": tenant_id}
        self.query_params = {}

async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get latest event and tenant
        event_res = await db.execute(text("SELECT id, tenant_id FROM events ORDER BY created_at DESC LIMIT 1"))
        event_row = event_res.mappings().first()
        if not event_row:
            print("No events found")
            return
        
        eid = event_row['id']
        tid = event_row['tenant_id']
        print(f"Using Event: {eid} | Tenant: {tid}")

        # Get a real user with access to this tenant from memberships
        user_res = await db.execute(text("""
            SELECT user_id
            FROM memberships
            WHERE tenant_id = :tid
            LIMIT 1
        """), {"tid": str(tid)})
        user_row = user_res.mappings().first()
        if not user_row:
            print("No memberships found for tenant")
            return
        user_id = user_row['user_id']

        # Let's count how many invitations exist in total for this event and tenant
        count_res = await db.execute(text("""
            SELECT COUNT(*) as count
            FROM invitations
            WHERE event_id = :eid AND tenant_id = :tid
        """), {"eid": str(eid), "tid": str(tid)})
        print(f"Total invitations: {count_res.scalar()}")

        # Let's print the actual pdf_url and zip_url of invitations to see what they look like
        sample_res = await db.execute(text("""
            SELECT id, pdf_url, zip_url, md5(COALESCE(pdf_url, '') || '|' || COALESCE(zip_url, '')) AS calculated_hash
            FROM invitations
            WHERE event_id = :eid AND tenant_id = :tid AND (pdf_url IS NOT NULL OR zip_url IS NOT NULL)
            LIMIT 3
        """), {"eid": str(eid), "tid": str(tid)})
        samples = list(sample_res.mappings())
        if samples:
            target_hash = samples[0]['calculated_hash']
            print(f"\nQuerying operation_id: {target_hash}")
            
            # Manual query using the db session
            manual_res = await db.execute(
                text("""
                    SELECT *
                    FROM invitations
                    WHERE event_id = :eid
                      AND tenant_id = :tid
                      AND md5(COALESCE(pdf_url, '') || '|' || COALESCE(zip_url, '')) = :opid
                      AND (metadata IS NULL OR metadata->>'generation_deleted' IS DISTINCT FROM 'true')
                """),
                {"eid": str(eid), "tid": str(tid), "opid": target_hash},
            )
            print(f"Manual query directly in db session returned: {len(manual_res.fetchall())} items.")
            
            # Mock User
            user = CurrentUser(id=user_id, email="test@test.com", role="admin")
            req = MockRequest(str(tid))
            
            # Call endpoint directly
            res = await get_generation_operation_details(
                event_id=eid,
                operation_id=target_hash,
                http_request=req,
                user=user,
                db=db
            )
            print(f"Returned from API: {len(res)} items")

asyncio.run(main())
