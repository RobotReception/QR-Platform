"""
╔══════════════════════════════════════════════════════════════════╗
║     اختبار شامل: إنشاء حساب + تسجيل الدخول + تهيئة المستأجر     ║
║     Da3wa Platform — Professional Auth & Provisioning Test      ║
╚══════════════════════════════════════════════════════════════════╝

يختبر كامل دورة حياة المستخدم الجديد:
  1. Pre-flight → فحص السيرفر + الخطط
  2. Signup  → إنشاء حساب + مستأجر + ملف شخصي + اشتراك
  3. Login   → تسجيل دخول + توكنات
  4. /auth/me → بيانات المستخدم الحالي
  5. Profile  → الملف الشخصي
  6. Tenant Provisioning → أدوار + إعدادات + Feature Flags + اشتراك
  7. Negative → تسجيل مكرر + كلمة مرور خاطئة
"""

import json
import sys
import time
import random
import string
import urllib.request
import urllib.error
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

# ══════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════
SERVER_HOST = "http://localhost:8019"
BASE_URL = f"{SERVER_HOST}/api/v1"
rand_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
TEST_EMAIL = f"test_prov_{rand_id}@test.com"
TEST_PASSWORD = "SecureP@ss2026!"
TEST_FULL_NAME = "محمد الاختبار"
TEST_ORG_NAME = f"شركة الاختبار {rand_id}"

# Expected provisioning data
EXPECTED_ROLES_MIN = 3      # At least Admin, Member, Viewer from DB function
EXPECTED_SETTINGS_MIN = 10  # At least 10 default settings
EXPECTED_FLAGS_MIN = 5      # At least 5 feature flags

# ══════════════════════════════════════════════
# TEST FRAMEWORK
# ══════════════════════════════════════════════
class TestResults:
    def __init__(self):
        self.results: list[dict] = []
        self.current_phase = ""
        self.phase_num = 0
        self.start_time = time.time()

    def set_phase(self, name: str):
        self.phase_num += 1
        self.current_phase = name
        print(f"\n{'━' * 60}")
        print(f"  المرحلة {self.phase_num}: {name}")
        print(f"{'━' * 60}")

    def check(self, label: str, passed: bool, detail: str = "") -> bool:
        self.results.append({
            "phase": self.current_phase,
            "label": label,
            "passed": passed,
            "detail": detail,
        })
        icon = "✅" if passed else "❌"
        suffix = f"  ← {detail}" if detail else ""
        print(f"  {icon} {label}{suffix}")
        return passed

    def print_summary(self):
        elapsed = time.time() - self.start_time
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed

        print(f"\n{'═' * 60}")
        print(f"  📊 ملخص النتائج")
        print(f"{'═' * 60}")
        print(f"  ⏱  الوقت: {elapsed:.2f} ثانية")
        print(f"  📝 الاختبارات: {total}")
        print(f"  ✅ ناجح: {passed}")
        if failed > 0:
            print(f"  ❌ فاشل: {failed}")
        print(f"{'─' * 60}")

        if failed == 0:
            print(f"  🎉 جميع الاختبارات نجحت! ALL {total} TESTS PASSED!")
        else:
            print(f"  ⚠️  الاختبارات الفاشلة:")
            for r in self.results:
                if not r["passed"]:
                    print(f"     ❌ [{r['phase']}] {r['label']}")
                    if r["detail"]:
                        print(f"        → {r['detail']}")

        print(f"{'═' * 60}")

        # Phase breakdown
        print(f"\n  📋 تفصيل المراحل:")
        phases = {}
        for r in self.results:
            p = r["phase"]
            if p not in phases:
                phases[p] = {"total": 0, "passed": 0}
            phases[p]["total"] += 1
            if r["passed"]:
                phases[p]["passed"] += 1

        for phase, counts in phases.items():
            icon = "✅" if counts["passed"] == counts["total"] else "❌"
            print(f"     {icon} {phase}: {counts['passed']}/{counts['total']}")

        print()
        return failed == 0


def api(method: str, path: str, body=None, token=None, tenant_id=None,
        base_url=None) -> tuple[int, dict]:
    """Make an API call and return (status_code, response_body)."""
    url = f"{base_url or BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if tenant_id:
        headers["X-Tenant-ID"] = str(tenant_id)

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
            return e.code, json.loads(raw) if raw else {"error": str(e)}
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


# ══════════════════════════════════════════════
# MAIN TEST
# ══════════════════════════════════════════════
def main():
    t = TestResults()

    print(f"╔{'═' * 58}╗")
    print(f"║  Da3wa Platform — Auth & Provisioning Test Suite           ║")
    print(f"║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                       ║")
    print(f"╚{'═' * 58}╝")
    print(f"  📧 Email:    {TEST_EMAIL}")
    print(f"  🏢 Org:      {TEST_ORG_NAME}")
    print(f"  🌐 Base URL: {BASE_URL}")

    # ──────────────────────────────────────────
    # 0. PRE-FLIGHT CHECKS
    # ──────────────────────────────────────────
    t.set_phase("فحوصات أولية (Pre-flight)")

    # 0a. Server health
    try:
        health_req = urllib.request.Request(f"{SERVER_HOST}/health")
        with urllib.request.urlopen(health_req, timeout=5) as resp:
            h_status = resp.status
            h_data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        h_status = 0
        h_data = {"error": str(e)}

    if not t.check("السيرفر يعمل", h_status == 200,
                   f"v{h_data.get('version', '?')}" if h_status == 200
                   else f"status={h_status}, {h_data.get('error', '')[:80]}"):
        print(f"\n  ⛔ السيرفر غير متاح!")
        print(f"     تأكد من تشغيل: python -m uvicorn app.main:app --port 8019")
        t.print_summary()
        sys.exit(1)

    # 0b. Plans exist (required for subscription creation)
    status, data = api("GET", "/plans")
    plans = data if isinstance(data, list) else []
    free_plan = next((p for p in plans if p.get("code") == "free"), None)
    if not t.check("خطة Free موجودة في قاعدة البيانات", free_plan is not None,
                   f"{len(plans)} plans found" if plans
                   else "⚠ لا توجد خطط! يجب تطبيق seed data"):
        print(f"\n  ⛔ جدول plans فارغ — يجب تطبيق بيانات البذر (seed):")
        print(f"     قم بتشغيل SQL التالي في Supabase SQL Editor:")
        print(f"     INSERT INTO plans (code, name, price_monthly, price_yearly,")
        print(f"       currency, sort_order, features) VALUES")
        print(f"       ('free', 'Free', 0, 0, 'USD', 1,")
        print(f"        '[\"3 أعضاء\", \"100 رسالة/شهر\"]')")
        print(f"     ON CONFLICT (code) DO NOTHING;")
        t.print_summary()
        sys.exit(1)

    print(f"  📌 Plans: {[p.get('code') for p in plans]}")

    # ══════════════════════════════════════════
    # PHASE 1: SIGNUP
    # ══════════════════════════════════════════
    t.set_phase("إنشاء الحساب (Signup)")

    status, data = api("POST", "/auth/signup", {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": TEST_FULL_NAME,
        "organization_name": TEST_ORG_NAME,
    })

    t.check("Status = 201 Created", status == 201,
            f"got {status}" + (f": {data.get('detail', '')[:80]}" if status != 201 else ""))

    user_id = data.get("user_id")
    t.check("user_id مُرجع", user_id is not None, user_id or "missing")

    tenants = data.get("tenants")
    t.check("tenants مُرجعة (≥1)", tenants is not None and len(tenants) >= 1,
            f"count={len(tenants)}" if tenants else "None")

    tenant_id = None
    if tenants and len(tenants) > 0:
        tenant = tenants[0]
        tenant_id = tenant.get("tenant_id")

        t.check("الدور = owner", tenant.get("role") == "owner", tenant.get("role", "?"))
        t.check("اسم المستأجر صحيح", tenant.get("name") == TEST_ORG_NAME,
                tenant.get("name", "?"))
        t.check("الحالة active أو trial",
                tenant.get("tenant_status") in ("active", "trial"),
                tenant.get("tenant_status", "?"))

        print(f"\n  📌 Tenant ID: {tenant_id}")
        print(f"  📌 Slug:      {tenant.get('slug')}")
        print(f"  📌 Plan:      {tenant.get('plan')}")
    else:
        # Mark remaining checks as failed
        t.check("الدور = owner", False, "no tenants returned")
        t.check("اسم المستأجر صحيح", False, "no tenants returned")
        t.check("الحالة active أو trial", False, "no tenants returned")
        if status != 201:
            print(f"  📛 Error: {json.dumps(data, ensure_ascii=False)[:400]}")

    if status != 201:
        print(f"\n  ⛔ Signup فشل — لا يمكن المتابعة")
        t.print_summary()
        sys.exit(1)

    time.sleep(1)  # Let Supabase propagate

    # ══════════════════════════════════════════
    # PHASE 2: LOGIN
    # ══════════════════════════════════════════
    t.set_phase("تسجيل الدخول (Login)")

    status, data = api("POST", "/auth/login", {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })

    t.check("Status = 200 OK", status == 200, f"got {status}")

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    t.check("access_token مُرجع", access_token is not None,
            f"{access_token[:20]}..." if access_token else "missing")
    t.check("refresh_token مُرجع", refresh_token is not None,
            "present" if refresh_token else "missing")

    login_tenants = data.get("tenants")
    t.check("tenants متاحة مع دور owner",
            login_tenants is not None and len(login_tenants) > 0
            and login_tenants[0].get("role") == "owner",
            f"role={login_tenants[0].get('role')}" if login_tenants else "no tenants")

    if not tenant_id and login_tenants:
        tenant_id = login_tenants[0].get("tenant_id")

    if not access_token:
        print(f"\n  ⛔ لا يمكن المتابعة بدون access_token")
        t.print_summary()
        sys.exit(1)

    # ══════════════════════════════════════════
    # PHASE 3: GET /auth/me
    # ══════════════════════════════════════════
    t.set_phase("بيانات المستخدم (GET /auth/me)")

    status, data = api("GET", "/auth/me", token=access_token)

    t.check("Status = 200", status == 200, f"got {status}")
    t.check("البريد الإلكتروني يطابق",
            data.get("email") == TEST_EMAIL, data.get("email", "?"))
    me_tenants = data.get("tenants")
    t.check("المستأجرات متاحة",
            me_tenants is not None and len(me_tenants) >= 1,
            f"count={len(me_tenants)}" if me_tenants else "None")

    if data.get("full_name"):
        print(f"  📌 Full Name: {data.get('full_name')}")

    # ══════════════════════════════════════════
    # PHASE 4: PROFILE
    # ══════════════════════════════════════════
    t.set_phase("الملف الشخصي (GET /profile/me)")

    status, data = api("GET", "/profile/me", token=access_token, tenant_id=tenant_id)

    t.check("Status = 200", status == 200, f"got {status}")
    t.check("full_name صحيح",
            data.get("full_name") == TEST_FULL_NAME,
            data.get("full_name", "?"))

    # ══════════════════════════════════════════
    # PHASE 5: TENANT PROVISIONING VERIFICATION
    # ══════════════════════════════════════════
    t.set_phase("تهيئة المستأجر (Provisioning)")

    if not tenant_id:
        t.check("الأدوار النظامية", False, "no tenant_id")
        t.check("الإعدادات الافتراضية", False, "no tenant_id")
        t.check("Feature Flags", False, "no tenant_id")
        t.check("الاشتراك النشط", False, "no tenant_id")
    else:
        # ── 5a. Roles ──
        status, data = api("GET", "/roles", token=access_token, tenant_id=tenant_id)
        if status == 200 and isinstance(data, list):
            role_names = {r.get("name") for r in data}
            # The DB provision_tenant function creates Admin, Member, Viewer
            # The manual provisioning creates Admin, Member, Designer, Check-in Staff, Viewer
            has_admin = "Admin" in role_names
            has_member = "Member" in role_names
            t.check(
                f"الأدوار ({len(data)} دور، يشمل Admin + Member)",
                len(data) >= EXPECTED_ROLES_MIN and has_admin and has_member,
                f"roles: {sorted(role_names)}"
            )

            # Report Admin permissions
            admin_role = next((r for r in data if r.get("name") == "Admin"), None)
            if admin_role:
                admin_perms = admin_role.get("permissions") or []
                print(f"  📌 Admin permissions: {len(admin_perms)} صلاحية")

            system_roles = [r for r in data if r.get("is_system_role")]
            print(f"  📌 System roles: {len(system_roles)}, Custom: {len(data) - len(system_roles)}")
        else:
            t.check("الأدوار النظامية", False, f"status={status}")

        # ── 5b. Settings ──
        status, data = api("GET", "/tenants/current/settings",
                           token=access_token, tenant_id=tenant_id)
        if status == 200 and isinstance(data, list):
            setting_keys = {s.get("key") for s in data}
            t.check(
                f"الإعدادات الافتراضية ({len(data)} إعداد)",
                len(data) >= EXPECTED_SETTINGS_MIN,
                f"keys: {sorted(list(setting_keys))[:6]}..."
            )
            # Verify key settings exist
            critical = {"timezone", "language"} & setting_keys
            print(f"  📌 Includes timezone & language: {len(critical) == 2}")
        elif status == 200 and isinstance(data, dict):
            # Settings might be returned as a dict
            t.check(
                f"الإعدادات الافتراضية ({len(data)} إعداد)",
                len(data) >= EXPECTED_SETTINGS_MIN,
                f"keys: {sorted(list(data.keys()))[:6]}..."
            )
        else:
            t.check("الإعدادات الافتراضية", False, f"status={status}")

        # ── 5c. Feature Flags ──
        status, data = api("GET", "/tenants/current/features",
                           token=access_token, tenant_id=tenant_id)
        if status == 200 and isinstance(data, list):
            flag_keys = {f.get("flag_key") for f in data}
            t.check(
                f"Feature Flags ({len(data)} علم)",
                len(data) >= EXPECTED_FLAGS_MIN,
                f"flags: {sorted(list(flag_keys))[:6]}..."
            )
            enabled = [f.get("flag_key") for f in data if f.get("enabled")]
            print(f"  📌 Enabled:  {len(enabled)} — {enabled[:5]}")
            print(f"  📌 Disabled: {len(data) - len(enabled)}")
        else:
            t.check("Feature Flags", False, f"status={status}")

        # ── 5d. Subscription ──
        status, data = api("GET", "/subscriptions/current",
                           token=access_token, tenant_id=tenant_id)
        if status == 200:
            sub_status = data.get("status")
            plan_info = data.get("plan")
            plan_label = plan_info.get("code") if isinstance(plan_info, dict) else (data.get("plan_id") or "?")
            t.check(
                "الاشتراك النشط (free plan)",
                sub_status in ("active", "trialing"),
                f"status={sub_status}, plan={plan_label}"
            )
        else:
            t.check("الاشتراك النشط", False, f"status={status}")

    # ══════════════════════════════════════════
    # PHASE 6: NEGATIVE TESTS
    # ══════════════════════════════════════════
    t.set_phase("اختبارات سلبية (Negative Tests)")

    # ── 6a. Duplicate signup ──
    status, data = api("POST", "/auth/signup", {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": TEST_FULL_NAME,
        "organization_name": "Duplicate Org",
    })
    t.check("تسجيل مكرر → خطأ (409 أو 400)",
            status in (400, 409),
            f"got {status}: {data.get('detail', '')[:80]}")

    # ── 6b. Wrong password login ──
    status, data = api("POST", "/auth/login", {
        "email": TEST_EMAIL,
        "password": "WrongPassword999!",
    })
    t.check("كلمة مرور خاطئة → 401",
            status == 401,
            f"got {status}: {data.get('detail', '')[:80]}")

    # ══════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════
    all_passed = t.print_summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
