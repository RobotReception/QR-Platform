import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from jose import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings

async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    
    async with engine.connect() as conn:
        # Get owner user from first tenant
        result = await conn.execute(text("""
            SELECT t.id as tenant_id, m.user_id
            FROM tenants t
            LEFT JOIN memberships m ON t.id = m.tenant_id
            WHERE m.status = 'active' AND m.role = 'owner'
            LIMIT 1
        """))

        row = result.mappings().first()
        if not row:
            print("[ERROR] No owner found in database")
            return

        tenant_id = str(row['tenant_id'])
        user_id = str(row['user_id'])

        JWT_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"

        # Generate a token valid for 30 days
        payload = {
            "sub": user_id,
            "email": "owner@example.com",
            "aud": "authenticated",
            "role": "authenticated",
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        # Save to file
        auth_data = {
            "access_token": token,
            "tenant_id": tenant_id,
            "user_id": user_id
        }

        with open('auth-data.json', 'w', encoding='utf-8') as f:
            json.dump(auth_data, f, indent=2)

        print("============================================================")
        print("🟢 SUCCESS: New auth token generated successfully (valid for 30 days)!")
        print(f"Tenant ID: {tenant_id}")
        print(f"User ID: {user_id}")
        print("============================================================")
        print("\n👇 To login, open http://localhost:5173/ in your browser, press F12, go to Console, and run this code:")
        print("------------------------------------------------------------")
        
        js_code = f"""localStorage.setItem('qentry_access_token', '{token}');
localStorage.setItem('qentry_tenant_id', '{tenant_id}');
localStorage.setItem('qentry_user', '{user_id}');
location.reload();"""
        print(js_code)
        print("------------------------------------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
