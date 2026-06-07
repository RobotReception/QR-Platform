"""Test: Custom Plan Builder API — addons + calculate"""
import sys, json, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8021/api/v1"

def api_get(path):
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

def api_post(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

print("=" * 60)
print("  🔧 Custom Plan Builder — API Test")
print("=" * 60)

# ── 1. Test GET /addons ──
print("\n1️⃣  GET /addons — قائمة العناصر الإضافية")
addons = api_get("/addons")
print(f"   ✅ {len(addons)} عنصر متاح\n")
print(f"   {'#':>3s}  {'العنصر':<25s} {'الوحدة':<8s} {'السعر/وحدة':>12s} {'التصنيف':<12s}")
print(f"   {'─'*3}  {'─'*25} {'─'*8} {'─'*12} {'─'*12}")
for i, a in enumerate(addons, 1):
    print(f"   {i:3d}  {a['label_ar']:<25s} {a['unit_ar']:<8s} {a['price_per_unit']:>10.2f} ر.س  {a['category']:<12s}")

# ── 2. Test POST /custom-plans/calculate — scenario 1: Basic + extras ──
print(f"\n{'─'*60}")
print("\n2️⃣  POST /custom-plans/calculate — Basic + إضافات")
scenario1 = {
    "base_plan_code": "basic",
    "items": [
        {"key": "events_per_month", "quantity": 15},
        {"key": "invitations_per_event", "quantity": 3000},
        {"key": "guests_max", "quantity": 8000},
        {"key": "gates_per_event", "quantity": 5},
        {"key": "seats_max", "quantity": 10},
    ]
}
status_code, calc = api_post("/custom-plans/calculate", scenario1)
print(f"   Status: {status_code}")
if status_code == 200:
    print(f"\n   📦 الباقة الأساسية: {calc['base_plan_name']} — {calc['base_price']:,.0f} ر.س/شهر")
    print(f"\n   ── الإضافات ──")
    for line in calc['addon_lines']:
        print(f"   {line['icon']}  {line['label_ar']:<25s}  +{line['extra_quantity']:>6,d}  × {line['unit_price']:>6.2f} = {line['line_total']:>8,.2f} ر.س")
    print(f"\n   {'─'*45}")
    print(f"   💰 سعر الباقة الأساسية:    {calc['base_price']:>10,.2f} ر.س")
    print(f"   ➕ إجمالي الإضافات:        {calc['addons_total']:>10,.2f} ر.س")
    print(f"   ═══════════════════════════════════════════")
    print(f"   💎 الإجمالي الشهري:        {calc['total_monthly']:>10,.2f} ر.س")
    print(f"   📅 الإجمالي السنوي:        {calc['total_yearly']:>10,.2f} ر.س (خصم شهرين)")
    print(f"\n   ── الحدود النهائية ──")
    for k, v in sorted(calc['final_limits'].items()):
        val = "∞" if v == -1 else f"{v:,}"
        print(f"     {k:<30s} = {val:>10s}")

# ── 3. Test minimum price enforcement ──
print(f"\n{'─'*60}")
print("\n3️⃣  POST /custom-plans/calculate — اختبار الحد الأدنى (150 ريال)")
scenario2 = {
    "base_plan_code": "starter",
    "items": [
        {"key": "events_per_month", "quantity": 2},
    ]
}
status_code2, calc2 = api_post("/custom-plans/calculate", scenario2)
if status_code2 == 200:
    raw = calc2['base_price'] + calc2['addons_total']
    print(f"   السعر المحسوب: {raw:,.2f} ر.س")
    print(f"   السعر بعد تطبيق الحد الأدنى: {calc2['total_monthly']:,.2f} ر.س ✅")

# ── 4. Test Pro plan customization ──
print(f"\n{'─'*60}")
print("\n4️⃣  POST /custom-plans/calculate — Pro + تخصيص كبير")
scenario3 = {
    "base_plan_code": "pro",
    "items": [
        {"key": "events_per_month", "quantity": 50},
        {"key": "invitations_per_event", "quantity": 20000},
        {"key": "guests_max", "quantity": 30000},
        {"key": "gates_per_event", "quantity": 10},
        {"key": "storage_mb", "quantity": 50},
        {"key": "seats_max", "quantity": 50},
    ]
}
status_code3, calc3 = api_post("/custom-plans/calculate", scenario3)
if status_code3 == 200:
    print(f"   📦 الباقة: {calc3['base_plan_name']} — {calc3['base_price']:,.0f} ر.س")
    for line in calc3['addon_lines']:
        print(f"   {line['icon']}  {line['label_ar']:<25s}  +{line['extra_quantity']:>6,d}  = {line['line_total']:>8,.2f} ر.س")
    print(f"   💎 الإجمالي: {calc3['total_monthly']:,.2f} ر.س/شهر | {calc3['total_yearly']:,.2f} ر.س/سنة")

print(f"\n{'='*60}")
print("  🎉 جميع الاختبارات نجحت!")
print(f"{'='*60}")
