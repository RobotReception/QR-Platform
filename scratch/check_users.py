import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')
import asyncio
from app.database import get_db
from sqlalchemy import text

async def main():
    async for db in get_db():
        # Get all tenants
        r = await db.execute(text("SELECT id, name, slug FROM tenants"))
        tenants = r.fetchall()
        print("TENANTS:")
        for t in tenants:
            print(f"  id={t[0]} name={t[1]} slug={t[2]}")

        # Get all memberships
        r = await db.execute(text("""
            SELECT m.tenant_id, t.name, m.user_id, p.full_name, m.role, m.status
            FROM memberships m
            JOIN tenants t ON t.id = m.tenant_id
            LEFT JOIN profiles p ON p.id = m.user_id
        """))
        memberships = r.fetchall()
        print("\nMEMBERSHIPS:")
        for m in memberships:
            print(f"  tenant='{m[1]}' user='{m[3]}' role='{m[4]}' status='{m[5]}'")

        # Get all membership roles mapping
        r = await db.execute(text("""
            SELECT mr.tenant_id, t.name, mr.user_id, p.full_name, r.name
            FROM membership_roles mr
            JOIN tenants t ON t.id = mr.tenant_id
            JOIN roles r ON r.id = mr.role_id
            LEFT JOIN profiles p ON p.id = mr.user_id
        """))
        mapping = r.fetchall()
        print("\nMEMBERSHIP ROLES MAPPING:")
        for mp in mapping:
            print(f"  tenant='{mp[1]}' user='{mp[3]}' role_assigned='{mp[4]}'")
        break

if __name__ == "__main__":
    asyncio.run(main())
