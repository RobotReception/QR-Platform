"""Full API test: login + get events."""
import asyncio
import sys
import urllib.request
import json
# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

BASE = "http://localhost:8030/api/v1"

def post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode()

def get(path, token, tenant_id):
    req = urllib.request.Request(
        BASE + path,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": tenant_id,
        },
        method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode()

# Try login
print("=== Testing API ===")
email = "admin@test.com"
password = "Admin@12345"

data, err = post("/auth/login", {"email": email, "password": password})
if err:
    print(f"Login failed: {err}")
    print("Trying to create account...")
    data, err = post("/auth/signup", {
        "email": email,
        "password": password,
        "full_name": "مدير الاختبار",
        "organization_name": "مساحة الاختبار"
    })
    if err:
        print(f"Signup also failed: {err}")
        sys.exit(1)
    print(f"Signup OK: {data.get('message')}")
    # Now login
    data, err = post("/auth/login", {"email": email, "password": password})
    if err:
        print(f"Login after signup failed: {err}")
        sys.exit(1)

token = data.get("access_token")
tenants = data.get("tenants", [])
print(f"Login OK!")
print(f"Token (first 40 chars): {token[:40] if token else 'NONE'}...")
print(f"Tenants: {[(t['name'], str(t['tenant_id'])) for t in tenants]}")

if not tenants:
    print("ERROR: No tenants!")
    sys.exit(1)

tenant_id = str(tenants[0]["tenant_id"])
print(f"\n=== GET /events with tenant_id={tenant_id} ===")

events, err = get("/events", token, tenant_id)
if err:
    print(f"GET /events ERROR: {err}")
else:
    print(f"GET /events OK! Count: {len(events)}")
    for e in events:
        print(f"  - [{e['status']}] {e['title']} (id={e['id'][:8]}...)")

# Try creating an event
print("\n=== POST /events ===")
new_event, err = post("/events", {
    "title": "فعالية الاختبار الرسمية",
    "start_date": "2026-06-15T18:00:00Z",
    "vip_quota": 50,
    "normal_quota": 200,
    "timezone": "Asia/Riyadh",
    "venue_country": "SA"
})

# For POST we need auth headers manually
import urllib.request
req = urllib.request.Request(
    BASE + "/events",
    data=json.dumps({
        "title": "فعالية الاختبار الرسمية",
        "start_date": "2026-06-15T18:00:00Z",
        "vip_quota": 50,
        "normal_quota": 200,
        "timezone": "Asia/Riyadh",
        "venue_country": "SA"
    }).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    },
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        result = json.loads(r.read())
        print(f"POST /events OK! New event: id={result['id'][:8]}... title={result['title']}")
except urllib.error.HTTPError as e:
    print(f"POST /events ERROR {e.code}: {e.read().decode()}")
