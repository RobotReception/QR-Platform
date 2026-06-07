import sys, json, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

url = "http://localhost:8021/api/v1/plans"
req = urllib.request.Request(url)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())
    print(f"Status: {resp.status}")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Status: {e.code}")
    print(f"Body: {body[:1000]}")
except Exception as e:
    print(f"Error: {e}")
