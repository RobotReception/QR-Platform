"""Simple endpoint tester - outputs to file to avoid terminal encoding issues"""
import json, sys, time, random, string, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8019/api/v1"
rid = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
LOG = []

def log(msg):
    LOG.append(msg)
    print(msg)

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

def main():
    log("=" * 60)
    log("USERS ENDPOINT TEST")
    log("=" * 60)

    # 1. SIGNUP
    log("\n--- SIGNUP ---")
    s, d = api("POST", "/auth/signup", {
        "email": f"utest_{rid}@test.com",
        "password": "SecureP@ss2026!",
        "full_name": "Test User",
        "organization_name": f"Test Org {rid}",
    })
    log(f"Signup: {s}")
    if s != 201:
        log(f"  ERROR: {json.dumps(d, ensure_ascii=False)[:300]}")
        return
    uid = d.get("user_id")
    tid = d["tenants"][0]["tenant_id"] if d.get("tenants") else None
    log(f"  user_id: {uid}")
    log(f"  tenant_id: {tid}")

    time.sleep(1)

    # 2. LOGIN
    log("\n--- LOGIN ---")
    s, d = api("POST", "/auth/login", {
        "email": f"utest_{rid}@test.com",
        "password": "SecureP@ss2026!",
    })
    log(f"Login: {s}")
    token = d.get("access_token")
    if not token:
        log(f"  ERROR: no token. {json.dumps(d, ensure_ascii=False)[:300]}")
        return
    log(f"  token: {token[:30]}...")

    # 3. LIST MEMBERS
    log("\n--- GET /tenants/current/members ---")
    s, d = api("GET", "/tenants/current/members", token=token, tid=tid)
    log(f"List members: {s}, count={len(d) if isinstance(d, list) else 'N/A'}")
    if s != 200:
        log(f"  ERROR: {json.dumps(d, ensure_ascii=False)[:300]}")

    # 4. CREATE MEMBER
    log("\n--- POST /tenants/current/members ---")
    s, d = api("POST", "/tenants/current/members", {
        "email": f"newuser_{rid}@test.com",
        "full_name": "New User",
        "password": "Test@Pass2026!",
        "role": "member",
    }, token=token, tid=tid)
    log(f"Create member: {s}")
    log(f"  Response: {json.dumps(d, ensure_ascii=False)[:400]}")
    new_uid = d.get("user_id") if s == 201 else None

    # 5. PATCH MEMBER (change role)
    if new_uid:
        log("\n--- PATCH /tenants/current/members/:id (role) ---")
        s, d = api("PATCH", f"/tenants/current/members/{new_uid}",
                  {"role": "viewer"}, token=token, tid=tid)
        log(f"Update role: {s}")
        log(f"  Response: {json.dumps(d, ensure_ascii=False)[:300]}")

        log("\n--- PATCH /tenants/current/members/:id (status) ---")
        s, d = api("PATCH", f"/tenants/current/members/{new_uid}",
                  {"status": "disabled"}, token=token, tid=tid)
        log(f"Update status: {s}")
        log(f"  Response: {json.dumps(d, ensure_ascii=False)[:300]}")

    # 6. LIST ROLES
    log("\n--- GET /roles ---")
    s, d = api("GET", "/roles", token=token, tid=tid)
    log(f"List roles: {s}")
    if isinstance(d, list):
        log(f"  count={len(d)}")
        if d:
            log(f"  keys: {list(d[0].keys())}")
            role_id = d[0].get("id")
    else:
        log(f"  Response: {json.dumps(d, ensure_ascii=False)[:300]}")
        role_id = None

    # 7. ASSIGN/UNASSIGN ROLE
    if new_uid and role_id:
        log(f"\n--- POST /roles/assign (member={new_uid}, role={role_id}) ---")
        s, d = api("POST", f"/roles/assign?member_id={new_uid}&role_id={role_id}",
                  token=token, tid=tid)
        log(f"Assign role: {s}")
        log(f"  Response: {json.dumps(d, ensure_ascii=False)[:300]}")

        log(f"\n--- POST /roles/unassign ---")
        s, d = api("POST", f"/roles/unassign?member_id={new_uid}&role_id={role_id}",
                  token=token, tid=tid)
        log(f"Unassign role: {s}")
        log(f"  Response: {json.dumps(d, ensure_ascii=False)[:300]}")

    # 8. CREATE INVITE
    log("\n--- POST /invites ---")
    s, d = api("POST", "/invites", {
        "email": f"invite_{rid}@test.com",
        "role": "member",
    }, token=token, tid=tid)
    log(f"Create invite: {s}")
    log(f"  Response: {json.dumps(d, ensure_ascii=False)[:300]}")
    invite_id = d.get("id") if s == 201 else None

    # 9. LIST INVITES
    log("\n--- GET /invites ---")
    s, d = api("GET", "/invites", token=token, tid=tid)
    log(f"List invites: {s}")
    if isinstance(d, list):
        log(f"  count={len(d)}")
    else:
        log(f"  Response: {json.dumps(d, ensure_ascii=False)[:300]}")

    # 10. REVOKE INVITE
    if invite_id:
        log(f"\n--- DELETE /invites/{invite_id} ---")
        s, d = api("DELETE", f"/invites/{invite_id}", token=token, tid=tid)
        log(f"Revoke invite: {s}")
        log(f"  Response: {json.dumps(d, ensure_ascii=False)[:300]}")

    # 11. REMOVE MEMBER
    if new_uid:
        log(f"\n--- DELETE /tenants/current/members/{new_uid} ---")
        s, d = api("DELETE", f"/tenants/current/members/{new_uid}",
                  token=token, tid=tid)
        log(f"Remove member: {s}")
        log(f"  Response: {json.dumps(d, ensure_ascii=False)[:300]}")

    # Write results to file
    log("\n" + "=" * 60)
    log("DONE")

    with open("test_users_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(LOG))

if __name__ == "__main__":
    main()
