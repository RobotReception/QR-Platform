import sys, asyncio
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

async def main():
    from app.database import get_db
    from sqlalchemy import text

    async for db in get_db():
        # Get all active memberships
        result = await db.execute(text("""
            SELECT tenant_id, user_id, role FROM memberships WHERE status = 'active'
        """))
        memberships = result.fetchall()
        print(f"Found {len(memberships)} active memberships.")

        role_map = {"owner": "Admin", "admin": "Admin", "member": "Member", "viewer": "Viewer"}

        for tid, uid, role in memberships:
            rbac_role_name = role_map.get(role, "Member")
            
            # Find the role ID
            r_res = await db.execute(
                text("SELECT id FROM roles WHERE tenant_id = :tid AND name = :name LIMIT 1"),
                {"tid": str(tid), "name": rbac_role_name}
            )
            role_id = r_res.scalar()
            
            if not role_id:
                print(f"⚠️ Role '{rbac_role_name}' not found for tenant {tid}. Skipping.")
                continue

            # Assign role
            await db.execute(
                text("""
                    INSERT INTO membership_roles (tenant_id, user_id, role_id)
                    VALUES (:tid, :uid, :rid)
                    ON CONFLICT DO NOTHING
                """),
                {"tid": str(tid), "uid": str(uid), "rid": str(role_id)}
            )
            print(f"✅ Assigned '{rbac_role_name}' role to user {uid} in tenant {tid}")

        await db.commit()
        print("Done!")
        break

asyncio.run(main())
