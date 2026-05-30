"""Debug: check permissions table structure and require_permission logic."""
import sys, asyncio
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

async def check():
    from app.database import get_db
    from sqlalchemy import text

    async for db in get_db():
        # 1. What columns does permissions table have?
        r = await db.execute(text("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema='public' AND table_name='permissions'
            ORDER BY ordinal_position
        """))
        cols = r.fetchall()
        print("permissions columns:", [c[0] for c in cols])

        # 2. Sample rows from permissions
        r2 = await db.execute(text("SELECT * FROM permissions LIMIT 5"))
        rows = r2.mappings().fetchall()
        if rows:
            print("Sample permissions rows:")
            for row in rows:
                print(f"  {dict(row)}")
        else:
            print("permissions table is EMPTY")

        # 3. Check role_permissions table
        r3 = await db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='role_permissions'
            ORDER BY ordinal_position
        """))
        rp_cols = [c[0] for c in r3.fetchall()]
        print(f"\nrole_permissions columns: {rp_cols}")

        # 4. What does require_permission actually query?
        # Check the permission_service
        break

asyncio.run(check())
