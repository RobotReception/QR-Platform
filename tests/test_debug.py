"""Quick test to see exact error responses from create_member and invite"""
import json, sys, time, random, string, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8019/api/v1"
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

# Signup
s, d = api("POST", "/auth/signup", {
    "email": f"dbg_{rid}@test.com", "password": "SecureP@ss2026!",
    "full_name": "Debug User", "organization_name": f"Debug Org {rid}",
})
assert s == 201, f"Signup failed: {s} {d}"
uid = d["user_id"]
tid = d["tenants"][0]["tenant_id"]
time.sleep(1)

# Login
s, d = api("POST", "/auth/login", {"email": f"dbg_{rid}@test.com", "password": "SecureP@ss2026!"})
assert s == 200, f"Login failed: {s}"
token = d["access_token"]

print("="*60)
print("TEST 1: POST /tenants/current/members")
print("="*60)
s, d = api("POST", "/tenants/current/members", {
    "email": f"new_{rid}@test.com",
    "full_name": "New User",
    "password": "Test@Pass2026!",
    "role": "member",
}, token=token, tid=tid)
print(f"Status: {s}")
print(f"Response: {json.dumps(d, ensure_ascii=False, indent=2)}")

print()
print("="*60)
print("TEST 2: POST /invites")
print("="*60)
s2, d2 = api("POST", "/invites", {
    "email": f"inv_{rid}@test.com",
    "role": "member",
}, token=token, tid=tid)
print(f"Status: {s2}")
print(f"Response: {json.dumps(d2, ensure_ascii=False, indent=2)}")

if s == 201:
    new_uid = d.get("user_id")
    print()
    print("="*60)
    print("TEST 3: PATCH (change role)")
    print("="*60)
    s3, d3 = api("PATCH", f"/tenants/current/members/{new_uid}", {"role": "viewer"}, token=token, tid=tid)
    print(f"Status: {s3}")
    print(f"Response: {json.dumps(d3, ensure_ascii=False, indent=2)}")

    print()
    print("="*60)
    print("TEST 4: DELETE (remove member)")
    print("="*60)
    s4, d4 = api("DELETE", f"/tenants/current/members/{new_uid}", token=token, tid=tid)
    print(f"Status: {s4}")
    print(f"Response: {json.dumps(d4, ensure_ascii=False, indent=2)}")
