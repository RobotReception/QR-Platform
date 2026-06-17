"""Debug: check roles, memberships, and run user_has_permission test."""
import sys, asyncio
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

async def check():
    from app.database import get_db
    from sqlalchemy import text

    async for db in get_db():
        # 1. Check roles table columns
        r = await db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='roles'
            ORDER BY ordinal_position
        """))
        print("roles columns:", [c[0] for c in r.fetchall()])

        # 2. Sample roles
        r2 = await db.execute(text("SELECT * FROM roles LIMIT 5"))
        rows = r2.mappings().fetchall()
        print(f"roles count snippet:")
        for row in rows:
            print(f"  {dict(row)}")

        # 3. Memberships
        r3 = await db.execute(text("""
            SELECT m.user_id, m.role, m.status, m.tenant_id
            FROM memberships m LIMIT 5
        """))
        members = r3.fetchall()
        print(f"\nmemberships (first 5):")
        for m in members:
            print(f"  user={str(m[0])[:8]} role={m[1]} status={m[2]} tenant={str(m[3])[:8]}")

        # 4. Check user_has_permission function definition
        r4 = await db.execute(text("""
            SELECT pg_get_functiondef(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public' AND p.proname = 'user_has_permission'
        """))
        func_def = r4.scalar()
        if func_def:
            print(f"\nuser_has_permission function (first 800 chars):\n{func_def[:800]}")
        else:
            print("user_has_permission NOT FOUND!")

        # 5. Try calling the function with a real membership
        if members:
            tid = str(members[0][3])
            uid = str(members[0][0])
            try:
                r5 = await db.execute(text(
                    "SELECT public.user_has_permission(:tid::uuid, :uid::uuid, 'events.view')"
                ), {"tid": tid, "uid": uid})
                result = r5.scalar()
                print(f"\nuser_has_permission(tid={tid[:8]}, uid={uid[:8]}, 'events.view') = {result}")
            except Exception as e:
                print(f"\nuser_has_permission ERROR: {e}")
        
        break

asyncio.run(check())
