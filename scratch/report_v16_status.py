"""Generate full post-migration v16 status report."""
import asyncio
import json
import sys

import asyncpg

DB = dict(host="localhost", port=5434, user="postgres", password="postgres", database="postgres")


async def main():
    sys.stdout.reconfigure(encoding="utf-8")
    conn = await asyncpg.connect(**DB)

    report = {}

    report["tenants"] = await conn.fetch(
        "SELECT id, name, slug, plan, status FROM public.tenants ORDER BY created_at"
    )
    report["tenant_count"] = len(report["tenants"])

    report["ui_permission_count"] = await conn.fetchval(
        "SELECT COUNT(*) FROM public.permissions WHERE key LIKE 'ui.%'"
    )
    report["legacy_permission_count"] = await conn.fetchval(
        "SELECT COUNT(*) FROM public.permissions WHERE key NOT LIKE 'ui.%'"
    )
    report["ui_role_perm_rows"] = await conn.fetchval(
        "SELECT COUNT(*) FROM public.role_permissions WHERE permission_key LIKE 'ui.%'"
    )

    report["roles_by_tenant"] = await conn.fetch(
        """
        SELECT t.name AS tenant, r.name AS role, r.is_system_role,
               COUNT(rp.permission_key) AS total_perms,
               COUNT(rp.permission_key) FILTER (WHERE rp.permission_key LIKE 'ui.%%') AS ui_perms
        FROM public.roles r
        JOIN public.tenants t ON t.id = r.tenant_id
        LEFT JOIN public.role_permissions rp ON rp.role_id = r.id
        GROUP BY t.name, r.name, r.is_system_role, r.id
        ORDER BY t.name, r.name
        """
    )

    report["duplicate_ui_grants"] = await conn.fetchval(
        """
        SELECT COUNT(*) FROM (
            SELECT role_id, permission_key, COUNT(*) AS c
            FROM public.role_permissions
            WHERE permission_key LIKE 'ui.%%'
            GROUP BY role_id, permission_key
            HAVING COUNT(*) > 1
        ) d
        """
    )

    report["users_with_roles"] = await conn.fetch(
        """
        SELECT p.email, t.name AS tenant, r.name AS role_name, m.role AS membership_role
        FROM public.membership_roles mr
        JOIN public.memberships m ON m.user_id = mr.user_id AND m.tenant_id = mr.tenant_id
        JOIN public.roles r ON r.id = mr.role_id
        JOIN public.tenants t ON t.id = mr.tenant_id
        LEFT JOIN public.profiles p ON p.id = mr.user_id
        WHERE m.status = 'active'
        ORDER BY t.name, p.email
        """
    )

    report["member_ui_sample"] = await conn.fetch(
        """
        SELECT rp.permission_key
        FROM public.role_permissions rp
        JOIN public.roles r ON r.id = rp.role_id
        WHERE r.name = 'Member' AND r.is_system_role = true
          AND rp.permission_key LIKE 'ui.%%'
        ORDER BY rp.permission_key
        LIMIT 5
        """
    )

    report["member_denied_actions"] = [
        "ui.event.action.delete",
        "ui.gates.action.delete",
        "ui.invitations.action.revoke",
        "ui.templates.action.delete",
        "ui.members.action.create",
        "ui.roles.action.manage",
        "ui.teams.action.archive",
    ]
    report["member_missing_denied"] = []
    for key in report["member_denied_actions"]:
        has = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM public.role_permissions rp
                JOIN public.roles r ON r.id = rp.role_id
                WHERE r.name = 'Member' AND r.is_system_role = true
                  AND rp.permission_key = $1
            )
            """,
            key,
        )
        if has:
            report["member_missing_denied"].append(key)

    # Permission bridge test for admin user
    admin_sample = await conn.fetchrow(
        """
        SELECT m.user_id, m.tenant_id, p.email
        FROM public.memberships m
        JOIN public.profiles p ON p.id = m.user_id
        WHERE m.role IN ('owner', 'admin') AND m.status = 'active'
        LIMIT 1
        """
    )
    report["bridge_tests"] = []
    if admin_sample:
        uid, tid = admin_sample["user_id"], admin_sample["tenant_id"]
        for pkey in ["ui.invitations.action.generate", "invitations.create", "settings.manage"]:
            ok = await conn.fetchval(
                "SELECT public.user_has_permission($1, $2, $3)", tid, uid, pkey
            )
            report["bridge_tests"].append({"user": admin_sample["email"], "permission": pkey, "allowed": ok})

    await conn.close()
    print(json.dumps({k: (list(v) if hasattr(v, '__iter__') and not isinstance(v, (str, int, bool, list)) else v)
                      for k, v in report.items()}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
