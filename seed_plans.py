"""
Seed the database via Supabase REST API (http://localhost:8000).
Creates plans, plan_limits, and subscriptions tables if missing,
then seeds the plans data.
"""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

SUPABASE_URL = "http://localhost:8000"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJzZXJ2aWNlX3JvbGUiLAogICAgImlzcyI6ICJzdXBhYmFzZS1kZW1vIiwKICAgICJpYXQiOiAxNjQxNzY5MjAwLAogICAgImV4cCI6IDE3OTk1MzU2MDAKfQ.DaYlNEoUrrEn2Ig7tqibS-PHK5vgusbcbo7X36XVt4Q"


def supabase_sql(sql: str) -> dict:
    """Execute SQL via Supabase's pg_query RPC (service role)."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/pg_query"
    body = json.dumps({"query": sql}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": resp.status, "data": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode()[:500]}
    except Exception as e:
        return {"status": 0, "error": str(e)}


def supabase_rest_get(table: str) -> list:
    """GET from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*"
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  GET /{table} error: {e.code} — {e.read().decode()[:200]}")
        return []
    except Exception as e:
        print(f"  GET /{table} error: {e}")
        return []


def supabase_rest_post(table: str, rows: list) -> dict:
    """POST to Supabase REST API (insert rows)."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    body = json.dumps(rows).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Prefer": "return=representation,resolution=ignore-duplicates",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": resp.status, "data": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode()[:500]}
    except Exception as e:
        return {"status": 0, "error": str(e)}


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Da3wa Platform — Database Seed Script           ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"  🌐 Supabase: {SUPABASE_URL}\n")

    # ── 1. Check if plans table exists (via REST API) ──
    print("1. Checking plans table...")
    plans = supabase_rest_get("plans")

    if isinstance(plans, list) and len(plans) > 0:
        print(f"  ✅ Plans already exist: {[p.get('code') for p in plans]}")
        return

    # Plans table might not exist — try to create it via SQL
    print("  ⚠️  Plans table empty or missing. Creating via SQL...")

    # Use Supabase SQL endpoint
    create_sql = """
    CREATE TABLE IF NOT EXISTS public.plans (
        id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        code            TEXT NOT NULL UNIQUE,
        name            TEXT NOT NULL,
        description     TEXT,
        price_monthly   NUMERIC(10, 2) NOT NULL DEFAULT 0,
        price_yearly    NUMERIC(10, 2),
        currency        TEXT NOT NULL DEFAULT 'USD',
        is_active       BOOLEAN NOT NULL DEFAULT true,
        features        JSONB DEFAULT '[]',
        sort_order      INT NOT NULL DEFAULT 0,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS public.plan_limits (
        id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        plan_id     UUID NOT NULL REFERENCES public.plans(id) ON DELETE CASCADE,
        key         TEXT NOT NULL,
        value       BIGINT NOT NULL,
        period      TEXT NOT NULL DEFAULT 'none',
        UNIQUE(plan_id, key)
    );

    CREATE TABLE IF NOT EXISTS public.subscriptions (
        id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        tenant_id                   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
        plan_id                     UUID NOT NULL REFERENCES public.plans(id),
        provider                    TEXT NOT NULL DEFAULT 'stripe',
        provider_customer_id        TEXT,
        provider_subscription_id    TEXT,
        status                      TEXT NOT NULL DEFAULT 'trialing',
        current_period_start        TIMESTAMPTZ,
        current_period_end          TIMESTAMPTZ,
        cancel_at_period_end        BOOLEAN NOT NULL DEFAULT false,
        trial_ends_at               TIMESTAMPTZ,
        canceled_at                 TIMESTAMPTZ,
        created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """

    result = supabase_sql(create_sql)
    if result.get("status") != 200:
        print(f"  ℹ️  SQL RPC not available ({result.get('status')}). Will try REST insert directly.")
    else:
        print("  ✅ Tables created via SQL RPC")

    # ── 2. Seed plans via REST API ──
    print("\n2. Seeding plans via REST API...")
    plans_data = [
        {
            "code": "free",
            "name": "Free",
            "description": "للبدء والتجربة",
            "price_monthly": 0,
            "price_yearly": 0,
            "currency": "USD",
            "sort_order": 1,
            "features": ["3 أعضاء", "100 رسالة/شهر", "500 MB تخزين", "50 طلب AI/شهر"],
        },
        {
            "code": "pro",
            "name": "Pro",
            "description": "للفرق المتوسطة",
            "price_monthly": 29.00,
            "price_yearly": 290.00,
            "currency": "USD",
            "sort_order": 2,
            "features": ["25 عضو", "5,000 رسالة/شهر", "10 GB تخزين", "2,000 طلب AI/شهر"],
        },
        {
            "code": "enterprise",
            "name": "Enterprise",
            "description": "للمؤسسات والشركات الكبيرة",
            "price_monthly": 99.00,
            "price_yearly": 990.00,
            "currency": "USD",
            "sort_order": 3,
            "features": ["أعضاء غير محدود", "رسائل غير محدودة", "100 GB تخزين"],
        },
    ]

    result = supabase_rest_post("plans", plans_data)
    if result.get("status") in (200, 201):
        data = result.get("data", [])
        print(f"  ✅ Plans seeded: {[p.get('code') for p in data]}")
    else:
        print(f"  ❌ Failed: {result}")
        print("  💡 You may need to create the plans table manually.")
        print("     Run schema_final.sql in Supabase SQL Editor:")
        print("     http://localhost:54323/project/default/sql")
        return

    # ── 3. Verify ──
    print("\n3. Verification:")
    plans = supabase_rest_get("plans")
    for p in plans:
        print(f"  📌 {p.get('code', '?'):12s} — {p.get('name', '?'):12s} — ${p.get('price_monthly', 0)}/mo")

    print(f"\n  ✅ Total plans: {len(plans)}")
    print("  🎉 Database ready for testing!")


if __name__ == "__main__":
    main()
