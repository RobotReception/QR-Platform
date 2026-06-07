import asyncio
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from jose import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    tenant_id = '4327e3d1-40e2-4a4c-af8c-71746bcc7903'  # pride idea
    
    # 1. Get owner user ID for pride idea
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT user_id FROM memberships WHERE tenant_id = :tid AND role = 'owner' LIMIT 1"),
            {"tid": tenant_id}
        )
        row = res.first()
        if not row:
            print("[ERROR] Owner not found for pride idea")
            return
        user_id = str(row[0])
        print(f"Found owner user_id: {user_id}")
        user_email = "owner@example.com"

    # 2. Generate JWT token
    JWT_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"
    payload = {
        "sub": user_id,
        "email": user_email,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(days=1)).timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    print("JWT Token generated.")

    # 3. Call checkout endpoint on backend (port 8021)
    url = f"http://localhost:8021/api/v1/subscriptions/checkout?plan_code=pro"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, data=b"", headers=headers, method="POST")
    print(f"Sending POST request to {url}...")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            print("\n--- API RESPONSE ---")
            print(json.dumps(body, indent=2))
            
            # Save token and headers to auth-data.json for pride idea so developer can use it
            with open('auth-data.json', 'w', encoding='utf-8') as f:
                json.dump({
                    "access_token": token,
                    "tenant_id": tenant_id,
                    "user_id": user_id
                }, f, indent=2)
            print("\nUpdated auth-data.json for pride idea tenant.")
            
    except urllib.error.HTTPError as e:
        print(f"[HTTP ERROR] Code: {e.code} - {e.read().decode()[:500]}")
        return
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return

    # 4. Verify updated state in database
    async with engine.connect() as conn:
        tenant_res = await conn.execute(
            text("SELECT name, plan FROM tenants WHERE id = :tid"),
            {"tid": tenant_id}
        )
        t_row = tenant_res.first()
        print(f"\n--- Post-upgrade check ---")
        print(f"Tenant Name: '{t_row[0]}' | Plan column: '{t_row[1]}'")
        
        sub_res = await conn.execute(
            text("""
                SELECT s.id, p.name AS plan_name, p.code AS plan_code, s.status, s.provider, s.current_period_end 
                FROM subscriptions s
                JOIN plans p ON p.id = s.plan_id
                WHERE s.tenant_id = :tid
                ORDER BY s.created_at DESC
                LIMIT 1
            """),
            {"tid": tenant_id}
        )
        sub = sub_res.first()
        print(f"Active Sub -> Plan: {sub[1]} ({sub[2]}) | Status: {sub[3]} | Provider: {sub[4]} | End: {sub[5]}")

if __name__ == "__main__":
    asyncio.run(main())
