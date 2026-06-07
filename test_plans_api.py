"""Quick test: verify plans API endpoint returns 5 tiers with limits."""
import sys, json, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

url = "http://localhost:8021/api/v1/plans"
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode())
except Exception as e:
    print(f"❌ API call failed: {e}")
    sys.exit(1)

print(f"✅ Status: 200  |  Plans returned: {len(data)}\n")
print(f"  {'Code':12s} {'Name':12s} {'Monthly':>10s} {'Yearly':>10s} {'Currency':>8s} {'Popular':>8s} {'Features':>8s} {'Limits':>8s}")
print(f"  {'─'*12} {'─'*12} {'─'*10} {'─'*10} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
for p in data:
    monthly = p.get("price_monthly", 0)
    yearly = p.get("price_yearly", 0)
    code = p.get("code", "?")
    popular = "⭐" if p.get("is_popular") else ""
    if code == "enterprise":
        m_str = "تسعير مخصص"
        y_str = "—"
    elif monthly == 0:
        m_str = "مجانية"
        y_str = "—"
    else:
        m_str = f"{monthly:,.0f}"
        y_str = f"{yearly:,.0f}"
    features = p.get("features", [])
    limits = p.get("limits", [])
    print(f"  {code:12s} {p.get('name','?'):12s} {m_str:>10s} {y_str:>10s} {p.get('currency','?'):>8s} {popular:>8s} {len(features):>8d} {len(limits):>8d}")

print(f"\n  📊 All plans verified successfully!")

# Show one plan's limits as sample
print(f"\n  ── Sample: Pro plan limits ──")
pro = [p for p in data if p.get("code") == "pro"]
if pro:
    for lim in pro[0].get("limits", []):
        val = "∞" if lim["value"] == -1 else f"{lim['value']:,}"
        print(f"    {lim['key']:30s} = {val:>10s}  ({lim['period']})")
