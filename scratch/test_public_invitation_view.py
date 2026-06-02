import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

BASE = "http://localhost:8020/api/v1"

# 1. Login to get token and tenant ID
email = "admin@test.com"
password = "Admin@12345"

req_login = urllib.request.Request(
    BASE + "/auth/login",
    data=json.dumps({"email": email, "password": password}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req_login, timeout=10) as r:
        login_res = json.loads(r.read())
except Exception as e:
    print(f"Failed to login: {e}")
    sys.exit(1)

auth_token = login_res.get("access_token")
tenant_id = str(login_res.get("tenants", [])[0]["tenant_id"])

# 2. Get events to find the test event
req_events = urllib.request.Request(
    BASE + "/events",
    headers={
        "Authorization": f"Bearer {auth_token}",
        "X-Tenant-ID": tenant_id
    },
    method="GET"
)

try:
    with urllib.request.urlopen(req_events, timeout=10) as r:
        events = json.loads(r.read())
except Exception as e:
    print(f"Failed to get events: {e}")
    sys.exit(1)

if not events:
    print("No events found!")
    sys.exit(1)

event_id = events[0]["id"]
print(f"Using event ID: {event_id}")

# 3. Create a fast generation operation with metadata
# The fast generation API accepts invitations list and layouts
# We will use /fast-invitations/generate endpoint
req_gen = urllib.request.Request(
    BASE + f"/fast-invitations/generate",
    data=json.dumps({
        "event_id": event_id,
        "invitations": [
            {
                "guest_name": "الضيف الخاص بالرابط",
                "ticket_class": "vip",
                "metadata": {
                    "الجهة": "وزارة الاتصالات",
                    "المنصب": "مدير عام",
                    "رقم الهاتف": "+966500000000"
                }
            }
        ],
        "generate_pdf": True,
        "generate_zip": False,
        "layout_config": {
            "rows": 3,
            "cols": 3,
            "page_size": "A4",
            "orientation": "portrait",
            "show_guest_name": True,
            "show_code_text": True
        }
    }).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
        "X-Tenant-ID": tenant_id
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req_gen, timeout=10) as r:
        gen_res = json.loads(r.read())
    print("Generation successful!")
except Exception as e:
    # Read the error body
    if hasattr(e, 'read'):
        print(f"Failed to generate: {e.read().decode()}")
    else:
        print(f"Failed to generate: {e}")
    sys.exit(1)

# 4. Get the generation operation ID from the history list
req_history = urllib.request.Request(
    BASE + f"/fast-invitations/history/{event_id}",
    headers={
        "Authorization": f"Bearer {auth_token}",
        "X-Tenant-ID": tenant_id
    },
    method="GET"
)

try:
    with urllib.request.urlopen(req_history, timeout=10) as r:
        history = json.loads(r.read())
except Exception as e:
    print(f"Failed to get generation history: {e}")
    sys.exit(1)

if not history:
    print("No generation history found!")
    sys.exit(1)

operation_id = history[0]["id"]
print(f"Operation ID (from history): {operation_id}")

# 5. Get operation details to find the invitation token
req_details = urllib.request.Request(
    BASE + f"/fast-invitations/history/{event_id}/{operation_id}",
    headers={
        "Authorization": f"Bearer {auth_token}",
        "X-Tenant-ID": tenant_id
    },
    method="GET"
)

try:
    with urllib.request.urlopen(req_details, timeout=10) as r:
        invitations = json.loads(r.read())
except Exception as e:
    print(f"Failed to get operation details: {e}")
    sys.exit(1)

if not invitations:
    print("No invitations generated in this operation!")
    sys.exit(1)

inv = invitations[0]
token = inv.get("token")
print(f"Invitation Token: {token}")
print(f"Invitation admin side metadata: {inv.get('metadata')}")

# 5. Fetch public invitation view (no auth needed)
req_public = urllib.request.Request(
    BASE + f"/invitations/view/{token}",
    method="GET"
)

try:
    with urllib.request.urlopen(req_public, timeout=10) as r:
        public_inv = json.loads(r.read())
    print("\n=== Public Invitation Response ===")
    print(json.dumps(public_inv, indent=2, ensure_ascii=False))
    
    # Assertions
    assert "metadata" in public_inv, "metadata field missing from public response!"
    assert public_inv["metadata"] is not None, "metadata field is null!"
    assert public_inv["metadata"].get("الجهة") == "وزارة الاتصالات", "Metadata values did not match!"
    print("\nSUCCESS: Public view endpoint correctly returned the user's custom metadata fields!")
except Exception as e:
    if hasattr(e, 'read'):
        print(f"Failed to fetch public invitation view: {e.read().decode()}")
    else:
        print(f"Failed to fetch public invitation view: {e}")
    sys.exit(1)
