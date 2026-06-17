import sys, json, urllib.request, urllib.error
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://localhost:8019/api/v1"
data = json.dumps({"email": "errtest22@test.com", "password": "Test123456!", "full_name": "Debug", "organization_name": "Debug Org"}).encode()
req = urllib.request.Request(f"{BASE}/auth/signup", data=data, headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode())
        print(f"Status: {resp.status}")
        print(f"tenants: {d.get('tenants')}")
        print(f"user_id: {d.get('user_id')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Status: {e.code}")
    print(f"Error: {body}")
