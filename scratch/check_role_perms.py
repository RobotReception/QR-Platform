import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')
import asyncio
from app.database import get_db
from sqlalchemy import text

async def main():
    async for db in get_db():
        tid = "4327e3d1-40e2-4a4c-af8c-71746bcc7903"
        uid = "1f7afb25-8dce-4967-85ed-599caf202060"
        r = await db.execute(text("""
            SELECT DISTINCT rp.permission_key
            FROM public.membership_roles mr
            JOIN public.role_permissions rp ON rp.role_id = mr.role_id
            WHERE mr.tenant_id = CAST(:tid AS uuid)
              AND mr.user_id = CAST(:uid AS uuid)
            ORDER BY rp.permission_key
        """), {"tid": tid, "uid": uid})
        rows = r.fetchall()
        print("Direct query output:")
        for row in rows:
            print(f"  {row[0]}")
        break

if __name__ == "__main__":
    asyncio.run(main())
