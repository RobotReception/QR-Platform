"""
Execute migration v16: Add pending_subscriptions table for PayPal
"""
import json
import urllib.request
import urllib.error

SUPABASE_URL = "http://127.0.0.1:54821"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"


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
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"status": resp.status, "data": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": e.read().decode()[:500]}
    except Exception as e:
        return {"status": 0, "error": str(e)}


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Qentry Platform — Migration v16: PayPal Support        ║")
    print("║  Adding pending_subscriptions table                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  🌐 Supabase: {SUPABASE_URL}\n")

    # Read migration SQL
    with open("supabase/migration_v16_paypal_pending_subscriptions.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    print("1. Executing migration SQL...")
    result = supabase_sql(sql)
    
    if result.get("status") in (200, 201):
        print("  ✅ Migration executed successfully")
        print(f"  📊 Result: {result.get('data', 'OK')}")
    else:
        print(f"  ❌ Migration failed: {result}")
        return

    # Verify table exists
    print("\n2. Verifying pending_subscriptions table...")
    verify_sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'pending_subscriptions'
        );
    """
    result = supabase_sql(verify_sql)
    if result.get("status") == 200:
        exists = result.get("data", [{}])[0].get("exists", False)
        if exists:
            print("  ✅ Table 'pending_subscriptions' exists")
        else:
            print("  ❌ Table 'pending_subscriptions' not found")
    else:
        print(f"  ⚠️  Verification failed: {result}")

    print("\n  🎉 Migration v16 completed!")


if __name__ == "__main__":
    main()
