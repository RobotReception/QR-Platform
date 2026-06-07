import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    tenant_id = '4327e3d1-40e2-4a4c-af8c-71746bcc7903' # pride idea
    
    async with engine.connect() as conn:
        # Check tenant plan column
        tenant_res = await conn.execute(
            text("SELECT name, plan FROM tenants WHERE id = :tid"),
            {"tid": tenant_id}
        )
        t_row = tenant_res.first()
        if t_row:
            print(f"Tenant Name: '{t_row[0]}' | Plan column: '{t_row[1]}'")
        else:
            print("Tenant 'pride idea' not found in database!")
            return
            
        # Check subscriptions table
        sub_res = await conn.execute(
            text("""
                SELECT s.id, p.name AS plan_name, p.code AS plan_code, s.status, s.current_period_end 
                FROM subscriptions s
                JOIN plans p ON p.id = s.plan_id
                WHERE s.tenant_id = :tid
                ORDER BY s.created_at DESC
            """),
            {"tid": tenant_id}
        )
        subs = sub_res.all()
        print("\n--- Subscriptions ---")
        for sub in subs:
            print(f"Sub ID: {sub[0]} | Plan: {sub[1]} ({sub[2]}) | Status: {sub[3]} | Period End: {sub[4]}")
            
        # Check active limits
        from app.services.usage_service import get_tenant_plan_limits
        from app.database import get_db
        # We need a session, let's create engine and sessionmaker
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
        SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with SessionLocal() as db:
            plan_code, limits = await get_tenant_plan_limits(db, tenant_id)
            print(f"\nResolved Active Plan: '{plan_code}'")
            print("Active Limits:")
            for limit in limits:
                print(f"  - {limit['key']}: {limit['value']} (Period: {limit['period']})")

if __name__ == "__main__":
    asyncio.run(main())
