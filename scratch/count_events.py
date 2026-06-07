import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')
import asyncio
from app.database import get_db
from sqlalchemy import text

async def main():
    async for db in get_db():
        r = await db.execute(text("""
            SELECT t.name, t.slug, COUNT(e.id) AS events_count
            FROM tenants t
            LEFT JOIN events e ON e.tenant_id = t.id
            GROUP BY t.name, t.slug
            ORDER BY events_count DESC
        """))
        rows = r.fetchall()
        print("Events per Tenant:")
        for row in rows:
            print(f"  - Tenant: '{row[0]}' (Slug: {row[1]}) -> Events Count: {row[2]}")
        break

if __name__ == "__main__":
    asyncio.run(main())
