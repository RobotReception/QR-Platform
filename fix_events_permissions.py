"""Fix: Add missing events/gates permissions and assign to owner/admin roles."""
import sys, asyncio
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

# All permissions needed by events.py
EVENTS_PERMISSIONS = [
    ("events.view",       "عرض الأحداث"),
    ("events.create",     "إنشاء حدث جديد"),
    ("events.edit",       "تعديل الأحداث"),
    ("events.delete",     "حذف الأحداث"),
    ("events.publish",    "نشر الأحداث"),
    ("events.transition", "تغيير حالة الأحداث"),
    ("gates.view",        "عرض بوابات الدخول"),
    ("gates.manage",      "إدارة بوابات الدخول"),
    ("invitations.view",  "عرض الدعوات"),
    ("invitations.create","إنشاء دعوات"),
    ("invitations.edit",  "تعديل الدعوات"),
    ("invitations.delete","حذف الدعوات"),
    ("assets.manage",     "إدارة أصول الأحداث"),
    ("checkin.view",      "عرض سجلات الدخول"),
    ("stats.view",        "عرض الإحصائيات"),
]

async def fix():
    from app.database import get_db
    from sqlalchemy import text

    async for db in get_db():
        # 1. Get existing permissions
        r = await db.execute(text("SELECT key FROM permissions"))
        existing = {row[0] for row in r.fetchall()}
        print(f"Existing permissions: {len(existing)}")

        # 2. Insert missing permissions
        added = []
        for key, desc in EVENTS_PERMISSIONS:
            if key not in existing:
                await db.execute(text("""
                    INSERT INTO permissions (key, description) VALUES (:key, :desc)
                    ON CONFLICT (key) DO NOTHING
                """), {"key": key, "desc": desc})
                added.append(key)

        if added:
            await db.commit()
            print(f"Added {len(added)} new permissions: {added}")
        else:
            print("All event/gate permissions already exist.")

        # 3. Get all roles with their tenant IDs
        r2 = await db.execute(text("""
            SELECT DISTINCT r.id, r.name, r.tenant_id
            FROM roles r
            WHERE r.name IN ('owner', 'admin', 'manager')
        """))
        roles = r2.fetchall()
        print(f"\nFound {len(roles)} owner/admin/manager roles across tenants")

        # 4. Assign all event+gate permissions to owner/admin/manager roles
        assigned = 0
        for role_id, role_name, tenant_id in roles:
            for key, _ in EVENTS_PERMISSIONS:
                try:
                    await db.execute(text("""
                        INSERT INTO role_permissions (role_id, permission_key)
                        VALUES (:rid, :pkey)
                        ON CONFLICT DO NOTHING
                    """), {"rid": str(role_id), "pkey": key})
                    assigned += 1
                except Exception as e:
                    print(f"  [warn] {role_name} + {key}: {e}")
        
        await db.commit()
        print(f"Ensured {assigned} role-permission assignments.")

        # 5. Verify user_has_permission function exists
        try:
            r3 = await db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_proc p
                    JOIN pg_namespace n ON n.oid = p.pronamespace
                    WHERE n.nspname = 'public' AND p.proname = 'user_has_permission'
                )
            """))
            exists = r3.scalar()
            print(f"\nuser_has_permission function exists: {exists}")
        except Exception as e:
            print(f"[ERR] checking function: {e}")

        # 6. Quick test: does any user have events.view permission?
        try:
            r4 = await db.execute(text("""
                SELECT m.user_id, m.role
                FROM memberships m
                WHERE m.status = 'active'
                LIMIT 3
            """))
            members = r4.fetchall()
            for uid, role in members:
                try:
                    r5 = await db.execute(text(
                        "SELECT public.user_has_permission(:tid, :uid, 'events.view')"
                    ), {"tid": str(tenant_id), "uid": str(uid)})
                    has = r5.scalar()
                    print(f"  user {str(uid)[:8]}... role={role} has events.view: {has}")
                except Exception as e:
                    print(f"  [ERR] user_has_permission test: {e}")
        except Exception as e:
            print(f"[ERR] member check: {e}")

        break

asyncio.run(fix())
