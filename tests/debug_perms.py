"""Debug: check permissions and gate creation."""
import sys, asyncio
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

async def check():
    from app.database import get_db
    from sqlalchemy import text

    async for db in get_db():
        # Check all permissions
        r = await db.execute(text("""
            SELECT code, name FROM permissions ORDER BY code
        """))
        perms = r.fetchall()
        print(f"Total permissions: {len(perms)}")
        gate_perms = [p for p in perms if 'gate' in p[0].lower() or 'event' in p[0].lower()]
        print("Event/Gate permissions:")
        for p in gate_perms:
            print(f"  {p[0]:30} {p[1]}")

        # Check all roles
        r2 = await db.execute(text("SELECT DISTINCT name FROM roles ORDER BY name"))
        roles = [r[0] for r in r2.fetchall()]
        print(f"\nRoles: {roles}")
        
        # Check owner role permissions
        r3 = await db.execute(text("""
            SELECT p.code FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            JOIN roles r ON r.id = rp.role_id
            WHERE r.name = 'owner'
            ORDER BY p.code
        """))
        owner_perms = [r[0] for r in r3.fetchall()]
        print(f"\nOwner permissions ({len(owner_perms)}):")
        event_related = [p for p in owner_perms if 'event' in p.lower() or 'gate' in p.lower()]
        print(f"  Event/Gate: {event_related}")
        
        break

asyncio.run(check())
