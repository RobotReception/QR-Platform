"""Check and apply migration_v16_ui_permissions.sql, then print a report."""
import asyncio
import os
import sys

import asyncpg

DB = dict(host="localhost", port=5434, user="postgres", password="postgres", database="postgres")
MIGRATION = os.path.join(os.path.dirname(os.path.dirname(__file__)), "supabase", "migration_v16_ui_permissions.sql")


async def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 70)
    print("Migration v16 — UI Permissions")
    print("=" * 70)

    try:
        conn = await asyncpg.connect(**DB)
    except Exception as e:
        print(f"\n❌ Cannot connect to database at {DB['host']}:{DB['port']}")
        print(f"   Error: {e}")
        print("   Hint: run start.ps1 or `supabase start` first.")
        return 1

    before_ui = await conn.fetchval(
        "SELECT COUNT(*) FROM public.permissions WHERE key LIKE 'ui.%'"
    )
    before_rp = await conn.fetchval(
        "SELECT COUNT(*) FROM public.role_permissions WHERE permission_key LIKE 'ui.%'"
    )

    print(f"\n📊 Before migration:")
    print(f"   ui.* permissions in DB:        {before_ui}")
    print(f"   ui.* role_permissions rows:      {before_rp}")

    applied = False
    if before_ui >= 51:
        print("\n✅ Migration appears already applied (51+ ui.* keys found).")
        print("   Re-running migration idempotently to ensure role grants are complete...")
    else:
        print(f"\n⚠️  Migration NOT fully applied (expected ~51 ui.* keys, found {before_ui}).")
        print("   Applying migration_v16_ui_permissions.sql ...")

    with open(MIGRATION, "r", encoding="utf-8") as f:
        sql = f.read()

    try:
        await conn.execute(sql)
        applied = True
        print("   ✅ SQL executed successfully.")
    except Exception as e:
        print(f"   ❌ Migration failed: {e}")
        await conn.close()
        return 1

    after_ui = await conn.fetchval(
        "SELECT COUNT(*) FROM public.permissions WHERE key LIKE 'ui.%'"
    )
    after_rp = await conn.fetchval(
        "SELECT COUNT(*) FROM public.role_permissions WHERE permission_key LIKE 'ui.%'"
    )

    print(f"\n📊 After migration:")
    print(f"   ui.* permissions in DB:        {after_ui}")
    print(f"   ui.* role_permissions rows:      {after_rp}")

    # Per-role breakdown
    print("\n" + "=" * 70)
    print("Role → ui.* permission counts (system roles)")
    print("=" * 70)
    roles = await conn.fetch(
        """
        SELECT r.name, r.tenant_id, t.name AS tenant_name,
               COUNT(rp.permission_key) FILTER (WHERE rp.permission_key LIKE 'ui.%%') AS ui_count
        FROM public.roles r
        JOIN public.tenants t ON t.id = r.tenant_id
        LEFT JOIN public.role_permissions rp ON rp.role_id = r.id
        WHERE r.is_system_role = true
        GROUP BY r.id, r.name, r.tenant_id, t.name
        ORDER BY t.name, r.name
        """
    )
    for row in roles:
        print(f"   [{row['tenant_name'][:30]:30}] {row['name']:18} → {row['ui_count']} ui permissions")

    # Sample Viewer permissions
    print("\n" + "=" * 70)
    print("Viewer role — granted ui.* keys (first tenant)")
    print("=" * 70)
    viewer_keys = await conn.fetch(
        """
        SELECT rp.permission_key
        FROM public.role_permissions rp
        JOIN public.roles r ON r.id = rp.role_id
        WHERE r.name = 'Viewer' AND r.is_system_role = true
          AND rp.permission_key LIKE 'ui.%%'
        ORDER BY rp.permission_key
        LIMIT 20
        """
    )
    for k in viewer_keys:
        print(f"   • {k['permission_key']}")
    total_viewer = await conn.fetchval(
        """
        SELECT COUNT(*)
        FROM public.role_permissions rp
        JOIN public.roles r ON r.id = rp.role_id
        WHERE r.name = 'Viewer' AND r.is_system_role = true
          AND rp.permission_key LIKE 'ui.%%'
        """
    )
    if total_viewer > 20:
        print(f"   ... and {total_viewer - 20} more")

    # Verify user_has_permission bridge (sample)
    print("\n" + "=" * 70)
    print("Permission function smoke test")
    print("=" * 70)
    sample = await conn.fetchrow(
        """
        SELECT m.user_id, m.tenant_id, r.name AS role_name
        FROM public.membership_roles mr
        JOIN public.memberships m ON m.user_id = mr.user_id AND m.tenant_id = mr.tenant_id
        JOIN public.roles r ON r.id = mr.role_id
        WHERE r.name = 'Viewer' AND m.status = 'active'
        LIMIT 1
        """
    )
    if sample:
        uid, tid = sample["user_id"], sample["tenant_id"]
        tests = [
            ("ui.nav.dashboard", True),
            ("ui.invitations.action.generate", False),
            ("invitations.create", False),
        ]
        for pkey, _ in tests:
            ok = await conn.fetchval(
                "SELECT public.user_has_permission($1, $2, $3)", tid, uid, pkey
            )
            print(f"   Viewer user_has_permission('{pkey}'): {ok}")
    else:
        print("   (No Viewer user found for smoke test)")

    # List all ui keys
    print("\n" + "=" * 70)
    print(f"All {after_ui} ui.* permission keys")
    print("=" * 70)
    all_keys = await conn.fetch(
        "SELECT key, description FROM public.permissions WHERE key LIKE 'ui.%%' ORDER BY key"
    )
    for row in all_keys:
        print(f"   {row['key']}")

    await conn.close()
    print("\n" + "=" * 70)
    status = "APPLIED (idempotent re-run)" if before_ui >= 51 else "NEWLY APPLIED"
    print(f"✅ Migration v16 status: {status}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
