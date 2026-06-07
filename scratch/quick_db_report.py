import asyncio, asyncpg, json, sys
sys.stdout.reconfigure(encoding="utf-8")

async def main():
    c = await asyncpg.connect(host="localhost", port=5434, user="postgres", password="postgres", database="postgres")
    tenants = await c.fetch("SELECT name, slug, plan, status FROM tenants")
    users = await c.fetch("""
        SELECT COALESCE(au.email, p.full_name, m.user_id::text) AS identity,
               m.role, t.name AS tenant
        FROM memberships m
        JOIN tenants t ON t.id = m.tenant_id
        LEFT JOIN profiles p ON p.id = m.user_id
        LEFT JOIN auth.users au ON au.id = m.user_id
        WHERE m.status = 'active'
        ORDER BY t.name, identity
    """)
    ui = await c.fetchval("SELECT COUNT(*) FROM permissions WHERE key LIKE 'ui.%'")
    dup = await c.fetchval("""
        SELECT COUNT(*) FROM (
            SELECT role_id, permission_key FROM role_permissions
            WHERE permission_key LIKE 'ui.%'
            GROUP BY role_id, permission_key HAVING COUNT(*) > 1
        ) x
    """)
    roles = await c.fetch("""
        SELECT t.name AS tenant, r.name AS role,
               COUNT(*) FILTER (WHERE rp.permission_key LIKE 'ui.%') AS ui_perms
        FROM roles r
        JOIN tenants t ON t.id = r.tenant_id
        LEFT JOIN role_permissions rp ON rp.role_id = r.id
        WHERE r.is_system_role
        GROUP BY t.name, r.name
        ORDER BY t.name, r.name
    """)
    role_assignments = await c.fetch("""
        SELECT COALESCE(au.email, p.full_name, mr.user_id::text) AS identity,
               t.name AS tenant, r.name AS rbac_role
        FROM membership_roles mr
        JOIN memberships m ON m.user_id = mr.user_id AND m.tenant_id = mr.tenant_id
        JOIN roles r ON r.id = mr.role_id
        JOIN tenants t ON t.id = mr.tenant_id
        LEFT JOIN profiles p ON p.id = mr.user_id
        LEFT JOIN auth.users au ON au.id = mr.user_id
        WHERE m.status = 'active'
        ORDER BY t.name, identity
    """)
    staff = await c.fetch("""
        SELECT COALESCE(au.email, p.full_name, p.id::text) AS identity,
               COALESCE(p.is_staff, false) AS is_staff
        FROM profiles p
        LEFT JOIN auth.users au ON au.id = p.id
        WHERE COALESCE(p.is_staff, false) = true
    """)
    await c.close()
    print(json.dumps({
        "tenants": [dict(x) for x in tenants],
        "users": [dict(x) for x in users],
        "ui_keys": ui,
        "duplicate_ui_grants": dup,
        "system_roles": [dict(x) for x in roles],
        "rbac_assignments": [dict(x) for x in role_assignments],
        "staff_users": [dict(x) for x in staff],
    }, ensure_ascii=False, indent=2))

asyncio.run(main())
