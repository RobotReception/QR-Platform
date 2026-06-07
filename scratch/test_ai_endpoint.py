import asyncio
import sys
import json
import httpx
from uuid import uuid4
from jose import jwt
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.config import get_settings

# Prevent Windows console encoding issues
sys.stdout.reconfigure(encoding="utf-8")

settings = get_settings()

async def test():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("🧪 Testing AI Template Generator Endpoint via API")
        print("=" * 60)

        # 1. Fetch an existing user from the database (only id)
        user_res = await db.execute(text("SELECT id FROM profiles LIMIT 1"))
        user_row = user_res.mappings().first()
        if not user_row:
            print("❌ No users found in profiles. Please register a user first.")
            return

        user_id = str(user_row["id"])
        user_email = "test-ai-user@example.com"
        print(f"Using existing user: {user_id}")

        # 2. Generate JWT token for this user
        payload = {
            "sub": user_id,
            "email": user_email,
            "role": "authenticated"
        }
        # Sign token using local HS256 JWT secret
        token = jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")
        
        tenant_id = uuid4()
        tenant_name = f"Test AI Tenant {tenant_id.hex[:6]}"
        
        # 3. Insert test tenant and owner membership
        print(f"\n1. Creating test tenant '{tenant_name}' and owner membership...")
        await db.execute(
            text("INSERT INTO tenants (id, name, slug, plan, status) VALUES (:id, :name, :slug, 'starter', 'active')"),
            {"id": tenant_id, "name": tenant_name, "slug": f"test-ai-{tenant_id.hex[:6]}"}
        )
        
        # Insert owner membership
        await db.execute(
            text("INSERT INTO memberships (tenant_id, user_id, role, status) VALUES (:tid, :uid, 'owner', 'active')"),
            {"tid": tenant_id, "uid": UUID(user_id)}
        )
        await db.commit()

    # 4. Call endpoint as Starter plan (Should Fail with 403)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "Content-Type": "application/json"
    }
    
    body = {
        "prompt": "قالب بطاقة دعوة زفاف داكن وذهبي فخم",
        "ticket_class": "normal",
        "orientation": "portrait"
    }

    url = "http://localhost:8021/api/v1/templates/generate-ai"
    
    print("\n2. Calling /templates/generate-ai as Starter plan (Expecting 403 Forbidden)...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=body, timeout=10.0)
        print(f"   Status Code: {resp.status_code}")
        print(f"   Response Body: {resp.text}")
        assert resp.status_code == 403
        print("   ✅ Enforced AI features gate on Starter plan successfully!")

        # 5. Update tenant plan to Pro
        async with AsyncSessionLocal() as db:
            print("\n3. Updating tenant plan to Pro...")
            await db.execute(
                text("UPDATE tenants SET plan = 'pro' WHERE id = :id"),
                {"id": tenant_id}
            )
            await db.commit()

        # 6. Call endpoint as Pro plan (Should Succeed with 201)
        print("\n4. Calling /templates/generate-ai as Pro plan (Expecting 201 Created)...")
        resp = await client.post(url, headers=headers, json=body, timeout=10.0)
        print(f"   Status Code: {resp.status_code}")
        assert resp.status_code == 201
        
        data = resp.json()
        print(f"   Generated Template Name: {data['name']}")
        print(f"   Template Type: {data['template_type']}")
        print(f"   Background Color: {data['background_color']}")
        assert data['template_type'] == 'designed'
        assert data['background_color'] == '#1e293b' # prompt contained "dark"
        
        # Verify template elements were inserted
        async with AsyncSessionLocal() as db:
            elements_res = await db.execute(
                text("SELECT element_type, label FROM template_elements WHERE template_id = :tid"),
                {"tid": data['id']}
            )
            elements = elements_res.all()
            print(f"   Inserted elements count: {len(elements)}")
            for idx, el in enumerate(elements, 1):
                print(f"     Element {idx}: {el[0]} ({el[1]})")
            assert len(elements) == 5
            
        print("   ✅ AI template generation succeeded on Pro plan!")

    # 7. Clean up
    async with AsyncSessionLocal() as db:
        print("\n5. Cleaning up test database records...")
        await db.execute(text("DELETE FROM invite_templates WHERE tenant_id = :tid"), {"tid": tenant_id})
        await db.execute(text("DELETE FROM memberships WHERE tenant_id = :tid"), {"tid": tenant_id})
        await db.execute(text("DELETE FROM usage_counters WHERE tenant_id = :tid"), {"tid": tenant_id})
        await db.execute(text("DELETE FROM audit_logs WHERE tenant_id = :tid"), {"tid": tenant_id})
        await db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tenant_id})
        await db.commit()
        print("   ✅ Cleanup done.")

    print("\n" + "=" * 60)
    print("🎉 API Integration Test for AI Template Generation passed!")
    print("=" * 60)

if __name__ == '__main__':
    from uuid import UUID
    asyncio.run(test())
