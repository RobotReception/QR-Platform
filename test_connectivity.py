import urllib.request, json, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

results = []

# 1. Backend Health
try:
    r = urllib.request.urlopen('http://localhost:8030/health', timeout=5)
    data = json.loads(r.read())
    results.append(f"BACKEND_HEALTH: OK - {data}")
except Exception as e:
    results.append(f"BACKEND_HEALTH: FAILED - {e}")

# 2. Supabase REST API
try:
    anon = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0'
    req = urllib.request.Request(
        'http://localhost:54321/rest/v1/',
        headers={'apikey': anon, 'Authorization': f'Bearer {anon}'}
    )
    r = urllib.request.urlopen(req, timeout=5)
    results.append(f"SUPABASE_REST: OK - status {r.status}")
except Exception as e:
    results.append(f"SUPABASE_REST: FAILED - {e}")

# 3. Auth endpoint test
try:
    payload = json.dumps({"email": "test@test.com", "password": "wrongpassword"}).encode()
    req = urllib.request.Request(
        'http://localhost:8030/api/v1/auth/login',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        r = urllib.request.urlopen(req, timeout=5)
        results.append(f"AUTH_ENDPOINT: OK - {r.status}")
    except urllib.error.HTTPError as he:
        body = json.loads(he.read())
        if he.code == 401:
            results.append(f"AUTH_ENDPOINT: OK - endpoint reachable, got 401 (correct behavior): {body.get('detail','')}")
        else:
            results.append(f"AUTH_ENDPOINT: REACHABLE - HTTP {he.code}: {body}")
except Exception as e:
    results.append(f"AUTH_ENDPOINT: FAILED - {e}")

for r in results:
    print(r)
