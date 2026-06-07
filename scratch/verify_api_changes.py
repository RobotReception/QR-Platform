import json, sys, time, random, string, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

BASE = "http://localhost:8021/api/v1"
rid = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

def api(method, path, body=None, token=None, tid=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    if tid: headers["X-Tenant-ID"] = str(tid)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
            return e.code, json.loads(raw) if raw else {"error": str(e)}
        except:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}

async def check_db_membership_roles(tenant_id, user_id):
    from app.database import get_db
    from sqlalchemy import text
    async for db in get_db():
        r = await db.execute(text("""
            SELECT mr.role_id, r.name
            FROM membership_roles mr
            JOIN roles r ON r.id = mr.role_id
            WHERE mr.tenant_id = CAST(:tid AS uuid) AND mr.user_id = CAST(:uid AS uuid)
        """), {"tid": tenant_id, "uid": user_id})
        rows = r.fetchall()
        return [row[1] for row in rows]

async def verify():
    # 1. SIGNUP
    print("1. Creating test tenant & owner...")
    s, d = api("POST", "/auth/signup", {
        "email": f"verify_{rid}@test.com",
        "password": "SecureP@ss2026!",
        "full_name": "Verify Owner",
        "organization_name": f"Verify Org {rid}",
    })
    if s != 201:
        print(f"❌ Signup failed: {s} {d}")
        return
    owner_id = d["user_id"]
    tenant_id = d["tenants"][0]["tenant_id"]
    print(f"   Created owner: {owner_id}, tenant: {tenant_id}")

    # 2. LOGIN
    print("2. Logging in as owner...")
    s, d = api("POST", "/auth/login", {
        "email": f"verify_{rid}@test.com",
        "password": "SecureP@ss2026!",
    })
    token = d.get("access_token")
    if not token:
        print(f"❌ Login failed: {s} {d}")
        return
    print("   LoggedIn successfully.")

    # 3. CREATE MEMBER
    print("3. Creating member user via API...")
    s, d = api("POST", "/tenants/current/members", {
        "email": f"verify_member_{rid}@test.com",
        "full_name": "Verify Member",
        "password": "MemberPassword2026!",
        "role": "member",
    }, token=token, tid=tenant_id)
    if s != 201:
        print(f"❌ Create member failed: {s} {d}")
        return
    member_id = d["user_id"]
    print(f"   Created member user: {member_id}")

    # Verify DB contains 'Member' role in membership_roles
    db_roles = await check_db_membership_roles(tenant_id, member_id)
    print(f"   DB membership_roles after creation: {db_roles}")
    if "Member" in db_roles:
        print("   ✅ SUCCESS: 'Member' role assigned in database!")
    else:
        print("   ❌ FAILURE: 'Member' role NOT assigned in database!")
        return

    # 4. UPDATE MEMBER ROLE -> viewer
    print("4. Updating member role to 'viewer' via API...")
    s, d = api("PATCH", f"/tenants/current/members/{member_id}", {
        "role": "viewer"
    }, token=token, tid=tenant_id)
    if s != 200:
        print(f"❌ Update member role to viewer failed: {s} {d}")
        return
    
    # Verify DB contains 'Viewer' role (and not 'Member')
    db_roles = await check_db_membership_roles(tenant_id, member_id)
    print(f"   DB membership_roles after updating to viewer: {db_roles}")
    if "Viewer" in db_roles and "Member" not in db_roles:
        print("   ✅ SUCCESS: 'Viewer' role assigned and old role deleted in database!")
    else:
        print("   ❌ FAILURE: role assignment incorrect in database!")
        return

    # 5. UPDATE MEMBER ROLE -> admin
    print("5. Updating member role to 'admin' via API...")
    s, d = api("PATCH", f"/tenants/current/members/{member_id}", {
        "role": "admin"
    }, token=token, tid=tenant_id)
    if s != 200:
        print(f"❌ Update member role to admin failed: {s} {d}")
        return
    
    # Verify DB contains 'Admin' role (and not 'Viewer')
    db_roles = await check_db_membership_roles(tenant_id, member_id)
    print(f"   DB membership_roles after updating to admin: {db_roles}")
    if "Admin" in db_roles and "Viewer" not in db_roles:
        print("   ✅ SUCCESS: 'Admin' role assigned and old role deleted in database!")
    else:
        print("   ❌ FAILURE: role assignment incorrect in database!")
        return

    # 6. DELETE MEMBER
    print("6. Deleting member user via API...")
    s, d = api("DELETE", f"/tenants/current/members/{member_id}", token=token, tid=tenant_id)
    if s != 204:
        print(f"❌ Delete member failed: {s} {d}")
        return
    print("   Deleted successfully.")

    print("\n🎉 ALL BACKEND CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(verify())
