"""Create missing DB functions via Supabase REST API."""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

SUPABASE_URL = "http://localhost:8000"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJzZXJ2aWNlX3JvbGUiLAogICAgImlzcyI6ICJzdXBhYmFzZS1kZW1vIiwKICAgICJpYXQiOiAxNjQxNzY5MjAwLAogICAgImV4cCI6IDE3OTk1MzU2MDAKfQ.DaYlNEoUrrEn2Ig7tqibS-PHK5vgusbcbo7X36XVt4Q"


def exec_sql(sql: str, label: str = "") -> bool:
    """Execute SQL via Supabase's PostgREST (service_role)."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    body = json.dumps({"sql_query": sql}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"  ✅ {label or 'OK'}: status={resp.status}")
            return True
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:300]
        # 404 means exec_sql RPC doesn't exist, try raw SQL via pg
        if e.code == 404:
            return exec_sql_via_pg(sql, label)
        print(f"  ❌ {label or 'FAIL'}: {e.code} — {err}")
        return False
    except Exception as e:
        print(f"  ❌ {label or 'FAIL'}: {e}")
        return False


def exec_sql_via_pg(sql: str, label: str = "") -> bool:
    """Execute SQL via asyncpg directly (fallback)."""
    try:
        import asyncio
        import asyncpg

        async def run():
            conn = await asyncpg.connect(
                "postgresql://postgres.your-tenant-id:your-super-secret-and-long-postgres-password@localhost:6543/postgres",
                statement_cache_size=0,
            )
            try:
                await conn.execute(sql)
                return True
            finally:
                await conn.close()

        result = asyncio.run(run())
        print(f"  ✅ {label or 'OK'} (via asyncpg)")
        return result
    except Exception as e:
        print(f"  ❌ {label or 'FAIL'}: {e}")
        return False


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Da3wa — Create Missing DB Functions             ║")
    print("╚══════════════════════════════════════════════════╝\n")

    # 1. user_has_permission function
    print("1. Creating user_has_permission function...")
    exec_sql("""
        CREATE OR REPLACE FUNCTION public.user_has_permission(
            p_tenant_id UUID,
            p_user_id UUID,
            p_permission_key TEXT
        )
        RETURNS BOOLEAN
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM public.memberships m
                WHERE m.tenant_id = p_tenant_id
                  AND m.user_id = p_user_id
                  AND m.status = 'active'
                  AND m.role IN ('owner', 'admin')
            )
            OR EXISTS (
                SELECT 1
                FROM public.membership_roles mr
                JOIN public.role_permissions rp ON rp.role_id = mr.role_id
                WHERE mr.tenant_id = p_tenant_id
                  AND mr.user_id = p_user_id
                  AND rp.permission_key = p_permission_key
            );
        $$;
    """, "user_has_permission")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
