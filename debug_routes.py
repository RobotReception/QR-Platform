"""Debug: list routes involving tenants/current/members and invites"""
import json, urllib.request

url = "http://localhost:8019/openapi.json"
req = urllib.request.Request(url)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode("utf-8"))

paths = data.get("paths", {})
print("=== ALL TENANT ROUTES ===")
for path in sorted(paths.keys()):
    if "tenant" in path.lower():
        methods = list(paths[path].keys())
        print(f"  {', '.join(m.upper() for m in methods):20s} {path}")

print("\n=== ALL INVITE ROUTES ===")
for path in sorted(paths.keys()):
    if "invite" in path.lower():
        methods = list(paths[path].keys())
        print(f"  {', '.join(m.upper() for m in methods):20s} {path}")

print("\n=== ALL ROLE ROUTES ===")
for path in sorted(paths.keys()):
    if "role" in path.lower():
        methods = list(paths[path].keys())
        print(f"  {', '.join(m.upper() for m in methods):20s} {path}")

# Check if POST /tenants/current/members exists
members_path = "/api/v1/tenants/current/members"
if members_path in paths:
    methods = list(paths[members_path].keys())
    print(f"\n=== {members_path} ===")
    print(f"  Methods: {methods}")
else:
    print(f"\n!!! {members_path} NOT FOUND in routes !!!")
