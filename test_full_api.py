"""Full end-to-end API test after fixes."""
import sys, json, urllib.request, urllib.error
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

BASE = "http://localhost:8020/api/v1"

def api(method, path, body=None, token=None, tenant_id=None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    if tenant_id: headers["X-Tenant-ID"] = tenant_id
    
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers=headers,
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

print("=" * 50)
print("STEP 1: Login")
status, data = api("POST", "/auth/login", {
    "email": "admin@test.com",
    "password": "Admin@12345"
})
print(f"  Status: {status}")

if status == 401 or (isinstance(data, str) and "401" in str(status)):
    print("  Login failed — trying signup first")
    s2, d2 = api("POST", "/auth/signup", {
        "email": "admin@test.com",
        "password": "Admin@12345",
        "full_name": "Admin Test",
        "organization_name": "Test Org"
    })
    print(f"  Signup: {s2} {d2 if isinstance(d2, str) else d2.get('message')}")
    status, data = api("POST", "/auth/login", {
        "email": "admin@test.com",
        "password": "Admin@12345"
    })

if isinstance(data, str):
    print(f"  ERROR: {data}")
    sys.exit(1)

token = data.get("access_token")
tenants = data.get("tenants", [])
print(f"  OK: {len(tenants)} tenant(s)")

if not tenants:
    print("  No tenants!")
    sys.exit(1)

tid = str(tenants[0]["tenant_id"])
print(f"  Tenant: {tenants[0].get('name')} ({tid[:8]}...)")

print("\nSTEP 2: GET /events")
status, events = api("GET", "/events", token=token, tenant_id=tid)
print(f"  Status: {status}")
if isinstance(events, list):
    print(f"  Count: {len(events)}")
    for e in events:
        print(f"    - [{e['status']}] {e['title']}")
    event_id = events[0]['id'] if events else None
else:
    print(f"  ERROR: {events}")
    event_id = None

print("\nSTEP 3: POST /events (create new)")
status, new_event = api("POST", "/events", {
    "title": "مؤتمر الذكاء الاصطناعي 2026",
    "start_date": "2026-08-20T18:00:00Z",
    "vip_quota": 100,
    "normal_quota": 500,
    "timezone": "Asia/Riyadh",
    "venue_country": "SA",
    "venue_name": "قاعة الملك فيصل",
    "venue_city": "الرياض"
}, token=token, tenant_id=tid)
print(f"  Status: {status}")
if isinstance(new_event, dict) and new_event.get('id'):
    event_id = new_event['id']
    print(f"  Created: {new_event['title']} (id={event_id[:8]}...)")
else:
    print(f"  ERROR: {new_event}")

if event_id:
    print(f"\nSTEP 4: POST /events/{event_id[:8]}.../gates")
    status, gate = api("POST", f"/events/{event_id}/gates", {
        "name": "البوابة الرئيسية",
        "name_ar": "Main Gate",
        "allowed_classes": ["vip", "normal"]
    }, token=token, tenant_id=tid)
    print(f"  Status: {status}")
    if isinstance(gate, dict) and gate.get('id'):
        print(f"  Gate created: {gate['name']} classes={gate.get('allowed_classes')}")
    else:
        print(f"  ERROR: {gate}")

    print(f"\nSTEP 5: GET /events/{event_id[:8]}.../gates")
    status, gates = api("GET", f"/events/{event_id}/gates", token=token, tenant_id=tid)
    print(f"  Status: {status}")
    if isinstance(gates, list):
        print(f"  Gates: {[g['name'] for g in gates]}")
    else:
        print(f"  ERROR: {gates}")

print("\n" + "=" * 50)
print("ALL TESTS COMPLETE")
