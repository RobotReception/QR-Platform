import sys, asyncio
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

async def check():
    from app.database import get_db
    from sqlalchemy import text

    async for db in get_db():
        # Let's list all memberships with full UUIDs
        r_all = await db.execute(text("SELECT user_id, tenant_id, role, status FROM memberships"))
        all_memberships = r_all.fetchall()
        print("All memberships:")
        for m in all_memberships:
            print(f"  user_id={m[0]}, tenant_id={m[1]}, role={m[2]}, status={m[3]}")
        
        if not all_memberships:
            print("No memberships found!")
            return

        # Let's check the first user
        m = all_memberships[0]
        user_id = str(m[0])
        tenant_id = str(m[1])
        
        # Or let's search specifically for role='member' if exists
        for row in all_memberships:
            if row[2] == 'member':
                user_id = str(row[0])
                tenant_id = str(row[1])
                break

        print(f"\nChecking user {user_id} in tenant {tenant_id}...")
        
        # 1. Check membership
        r = await db.execute(text("""
            SELECT role, status FROM memberships
            WHERE tenant_id = CAST(:tid AS uuid) AND user_id = CAST(:uid AS uuid)
        """), {"tid": tenant_id, "uid": user_id})
        membership = r.first()
        print(f"Membership details: {membership}")
        
        # 2. Check assigned roles in membership_roles
        r2 = await db.execute(text("""
            SELECT mr.role_id, r.name, r.description
            FROM membership_roles mr
            JOIN roles r ON r.id = mr.role_id
            WHERE mr.tenant_id = CAST(:tid AS uuid) AND mr.user_id = CAST(:uid AS uuid)
        """), {"tid": tenant_id, "uid": user_id})
        assigned_roles = r2.fetchall()
        print(f"Assigned roles in membership_roles: {assigned_roles}")
        
        # 3. Check all roles in this tenant
        r3 = await db.execute(text("""
            SELECT id, name, is_system_role FROM roles
            WHERE tenant_id = CAST(:tid AS uuid)
        """), {"tid": tenant_id})
        tenant_roles = r3.fetchall()
        print(f"All roles in this tenant: {tenant_roles}")
        
        # 4. Check user_has_permission outcomes
        for pkey in ['reports.view', 'events.view', 'ui.nav.dashboard', 'ui.event.tab.analytics']:
            r_bool = await db.execute(text("""
                SELECT public.user_has_permission(CAST(:tid AS uuid), CAST(:uid AS uuid), :pkey)
            """), {"tid": tenant_id, "uid": user_id, "pkey": pkey})
            val = r_bool.scalar()
            print(f"user_has_permission('{pkey}'): {val}")
            
        # 5. Also check get_user_permissions
        r_perms = await db.execute(text("""
            SELECT * FROM public.get_user_permissions(CAST(:tid AS uuid), CAST(:uid AS uuid))
        """), {"tid": tenant_id, "uid": user_id})
        perms = r_perms.fetchall()
        print(f"get_user_permissions count: {len(perms)}")
        print(f"get_user_permissions: {[p[0] for p in perms]}")
        
        break

asyncio.run(check())

