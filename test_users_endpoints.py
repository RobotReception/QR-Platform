"""
╔══════════════════════════════════════════════════════════════════╗
║     اختبار شامل: Endpoints صفحة إدارة المستخدمين               ║
║     Da3wa Platform — Users Management Endpoint Tests            ║
╚══════════════════════════════════════════════════════════════════╝

يختبر كامل endpoints صفحة المستخدمين:
  1. Pre-flight → فحص السيرفر + تسجيل/دخول
  2. GET /tenants/current/members → قائمة الأعضاء
  3. POST /tenants/current/members → إنشاء مستخدم مباشر
  4. PATCH /tenants/current/members/:id → تحديث دور/حالة
  5. DELETE /tenants/current/members/:id → إزالة عضو
  6. GET /roles → قائمة الأدوار
  7. POST /roles/assign → إسناد دور
  8. POST /roles/unassign → إزالة دور
  9. POST /invites → دعوة مستخدم
  10. GET /invites → قائمة الدعوات
  11. DELETE /invites/:id → إلغاء دعوة
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

# We need a real user — use the signup flow
TEST_EMAIL = f"test_users_{rand_id}@test.com"
TEST_PASSWORD = "SecureP@ss2026!"
TEST_FULL_NAME = "اختبار المستخدمين"
TEST_ORG_NAME = f"مؤسسة اختبار {rand_id}"

# For the create-member test
CREATE_EMAIL = f"created_{rand_id}@test.com"
CREATE_NAME = "مستخدم مُنشأ"
CREATE_PASSWORD = "Test@Pass2026!"

# For the invite test
INVITE_EMAIL = f"invite_{rand_id}@test.com"


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
    print(f"║  Da3wa — Users Management Endpoints Test Suite            ║")
    print(f"║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                       ║")
    print(f"╚{'═' * 58}╝")
    print(f"  📧 Owner Email:  {TEST_EMAIL}")
    print(f"  📧 Create Email: {CREATE_EMAIL}")
    print(f"  📧 Invite Email: {INVITE_EMAIL}")
    print(f"  🌐 Base URL:     {BASE_URL}")

    # ──────────────────────────────────────────
    # 0. PRE-FLIGHT: Server + Auth
    # ──────────────────────────────────────────
    t.set_phase("فحوصات أولية (Pre-flight)")

    # Check server health
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

    # Signup a fresh test user
    status, data = api("POST", "/auth/signup", {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": TEST_FULL_NAME,
        "organization_name": TEST_ORG_NAME,
    })

    t.check("Signup → 201", status == 201,
            f"got {status}: {data.get('detail', '')[:80]}" if status != 201 else f"user_id={data.get('user_id')}")

    if status != 201:
        print(f"  ⛔ Signup فشل — لا يمكن المتابعة")
        print(f"     Error: {json.dumps(data, ensure_ascii=False)[:300]}")
        t.print_summary()
        sys.exit(1)

    user_id = data.get("user_id")
    tenants = data.get("tenants", [])
    tenant_id = tenants[0].get("tenant_id") if tenants else None

    print(f"  📌 User ID:   {user_id}")
    print(f"  📌 Tenant ID: {tenant_id}")

    time.sleep(1)

    # Login to get access token
    status, data = api("POST", "/auth/login", {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    t.check("Login → 200", status == 200, f"got {status}")

    access_token = data.get("access_token")
    if not access_token:
        print(f"  ⛔ لا يمكن المتابعة بدون access_token")
        t.print_summary()
        sys.exit(1)

    print(f"  📌 Token: {access_token[:20]}...")

    # ══════════════════════════════════════════
    # PHASE 1: GET /tenants/current/members
    # ══════════════════════════════════════════
    t.set_phase("قائمة الأعضاء (GET /tenants/current/members)")

    status, data = api("GET", "/tenants/current/members",
                       token=access_token, tenant_id=tenant_id)

    t.check("Status = 200", status == 200, f"got {status}")
    t.check("الاستجابة مصفوفة", isinstance(data, list),
            f"type={type(data).__name__}")

    if isinstance(data, list) and len(data) > 0:
        t.check("يحتوي عضو واحد على الأقل (المالك)", len(data) >= 1,
                f"count={len(data)}")
        member = data[0]
        t.check("العضو يحتوي على user_id", "user_id" in member,
                str(list(member.keys())))
        t.check("العضو يحتوي على role", "role" in member, member.get("role", "?"))
        t.check("العضو يحتوي على status", "status" in member, member.get("status", "?"))
        t.check("العضو يحتوي على full_name", "full_name" in member,
                member.get("full_name", "?"))

        print(f"  📌 أعضاء: {len(data)}")
        for m in data[:3]:
            print(f"      • {m.get('full_name', '?')} — {m.get('role')} — {m.get('status')}")
    else:
        t.check("يحتوي عضو واحد على الأقل", False, f"data={data}")

    # ══════════════════════════════════════════
    # PHASE 2: POST /tenants/current/members (Create User)
    # ══════════════════════════════════════════
    t.set_phase("إنشاء مستخدم مباشر (POST /tenants/current/members)")

    status, data = api("POST", "/tenants/current/members", {
        "email": CREATE_EMAIL,
        "full_name": CREATE_NAME,
        "password": CREATE_PASSWORD,
        "role": "member",
    }, token=access_token, tenant_id=tenant_id)

    t.check("Status = 201 Created", status == 201,
            f"got {status}: {json.dumps(data, ensure_ascii=False)[:200]}" if status != 201 else "")

    created_user_id = None
    if status == 201:
        created_user_id = data.get("user_id")
        t.check("user_id مُرجع", created_user_id is not None, str(created_user_id))
        t.check("الدور = member", data.get("role") == "member", data.get("role", "?"))
        t.check("الحالة = active", data.get("status") == "active", data.get("status", "?"))
        t.check("الاسم صحيح", data.get("full_name") == CREATE_NAME,
                data.get("full_name", "?"))
        print(f"  📌 Created user_id: {created_user_id}")
    else:
        t.check("user_id مُرجع", False, "create failed")
        t.check("الدور = member", False, "create failed")
        t.check("الحالة = active", False, "create failed")
        t.check("الاسم صحيح", False, "create failed")
        print(f"  📛 Error: {json.dumps(data, ensure_ascii=False)[:400]}")

    # ── 2b: Duplicate create should fail ──
    if created_user_id:
        status2, data2 = api("POST", "/tenants/current/members", {
            "email": CREATE_EMAIL,
            "full_name": CREATE_NAME,
            "password": CREATE_PASSWORD,
            "role": "viewer",
        }, token=access_token, tenant_id=tenant_id)
        t.check("إنشاء مكرر → 409", status2 == 409,
                f"got {status2}: {data2.get('detail', '')[:80]}")

    # ── 2c: Invalid role should fail ──
    status3, data3 = api("POST", "/tenants/current/members", {
        "email": f"bad_role_{rand_id}@test.com",
        "full_name": "Bad Role",
        "password": "Test@Pass2026!",
        "role": "owner",
    }, token=access_token, tenant_id=tenant_id)
    t.check("دور owner → 400", status3 == 400,
            f"got {status3}: {data3.get('detail', '')[:80]}")

    # ══════════════════════════════════════════
    # PHASE 3: PATCH /tenants/current/members/:id (Update Role/Status)
    # ══════════════════════════════════════════
    t.set_phase("تحديث العضو (PATCH /tenants/current/members/:id)")

    if created_user_id:
        # ── 3a: Change role ──
        status, data = api("PATCH", f"/tenants/current/members/{created_user_id}",
                          {"role": "viewer"},
                          token=access_token, tenant_id=tenant_id)
        t.check("تغيير الدور → 200", status == 200,
                f"got {status}: {json.dumps(data, ensure_ascii=False)[:100]}" if status != 200 else "")
        if status == 200:
            t.check("الدور الجديد = viewer", data.get("role") == "viewer",
                    data.get("role", "?"))

        # ── 3b: Toggle status to disabled ──
        status, data = api("PATCH", f"/tenants/current/members/{created_user_id}",
                          {"status": "disabled"},
                          token=access_token, tenant_id=tenant_id)
        t.check("تعطيل العضو → 200", status == 200,
                f"got {status}" + (f": {data.get('detail', '')[:80]}" if status != 200 else ""))
        if status == 200:
            t.check("الحالة = disabled", data.get("status") == "disabled",
                    data.get("status", "?"))

        # ── 3c: Toggle status back to active ──
        status, data = api("PATCH", f"/tenants/current/members/{created_user_id}",
                          {"status": "active"},
                          token=access_token, tenant_id=tenant_id)
        t.check("تفعيل العضو → 200", status == 200, f"got {status}")
        if status == 200:
            t.check("الحالة = active", data.get("status") == "active",
                    data.get("status", "?"))

        # ── 3d: Cannot change own role ──
        status, data = api("PATCH", f"/tenants/current/members/{user_id}",
                          {"role": "member"},
                          token=access_token, tenant_id=tenant_id)
        t.check("تغيير دور النفس → 400", status == 400,
                f"got {status}: {data.get('detail', '')[:80]}")
    else:
        for label in ["تغيير الدور → 200", "الدور الجديد = viewer",
                      "تعطيل العضو → 200", "الحالة = disabled",
                      "تفعيل العضو → 200", "الحالة = active",
                      "تغيير دور النفس → 400"]:
            t.check(label, False, "no created_user_id")

    # ══════════════════════════════════════════
    # PHASE 4: GET /roles
    # ══════════════════════════════════════════
    t.set_phase("قائمة الأدوار (GET /roles)")

    status, data = api("GET", "/roles", token=access_token, tenant_id=tenant_id)

    t.check("Status = 200", status == 200, f"got {status}")
    if status == 200 and isinstance(data, list):
        t.check("يوجد أدوار (≥3)", len(data) >= 3, f"count={len(data)}")
        role_names = [r.get("name") for r in data]
        t.check("يوجد دور Admin", "Admin" in role_names, str(role_names[:6]))
        t.check("يحتوي على is_system_role", "is_system_role" in data[0],
                str(list(data[0].keys())))

        first_role_id = data[0].get("id") if data else None
        print(f"  📌 أدوار: {role_names[:6]}")
        print(f"  📌 First role ID: {first_role_id}")
    else:
        t.check("يوجد أدوار (≥3)", False, f"data type={type(data).__name__}")
        first_role_id = None

    # ══════════════════════════════════════════
    # PHASE 5: POST /roles/assign & /roles/unassign
    # ══════════════════════════════════════════
    t.set_phase("إسناد/إزالة الأدوار (POST /roles/assign & /roles/unassign)")

    if created_user_id and first_role_id:
        # Assign
        status, data = api("POST",
                          f"/roles/assign?member_id={created_user_id}&role_id={first_role_id}",
                          token=access_token, tenant_id=tenant_id)
        t.check("إسناد دور → 200", status == 200,
                f"got {status}: {json.dumps(data, ensure_ascii=False)[:100]}" if status != 200 else data.get("message", ""))

        # Unassign
        status, data = api("POST",
                          f"/roles/unassign?member_id={created_user_id}&role_id={first_role_id}",
                          token=access_token, tenant_id=tenant_id)
        t.check("إزالة دور → 200", status == 200,
                f"got {status}: {json.dumps(data, ensure_ascii=False)[:100]}" if status != 200 else data.get("message", ""))
    else:
        t.check("إسناد دور → 200", False,
                f"user={created_user_id}, role={first_role_id}")
        t.check("إزالة دور → 200", False, "missing IDs")

    # ══════════════════════════════════════════
    # PHASE 6: POST /invites (Create Invite)
    # ══════════════════════════════════════════
    t.set_phase("دعوة مستخدم (POST /invites)")

    status, data = api("POST", "/invites", {
        "email": INVITE_EMAIL,
        "role": "member",
    }, token=access_token, tenant_id=tenant_id)

    t.check("Status = 201 Created", status == 201,
            f"got {status}: {json.dumps(data, ensure_ascii=False)[:200]}" if status != 201 else "")

    invite_id = None
    if status == 201:
        invite_id = data.get("id")
        t.check("id مُرجع", invite_id is not None, str(invite_id))
        t.check("البريد صحيح", data.get("email") == INVITE_EMAIL,
                data.get("email", "?"))
        t.check("الحالة = pending", data.get("status") == "pending",
                data.get("status", "?"))
        t.check("الدور = member", data.get("role") == "member",
                data.get("role", "?"))
        print(f"  📌 Invite ID: {invite_id}")
    else:
        t.check("id مُرجع", False, "invite failed")
        t.check("البريد صحيح", False, "invite failed")
        t.check("الحالة = pending", False, "invite failed")
        t.check("الدور = member", False, "invite failed")
        print(f"  📛 Error: {json.dumps(data, ensure_ascii=False)[:400]}")

    # ── 6b: Duplicate invite should fail ──
    if invite_id:
        status2, data2 = api("POST", "/invites", {
            "email": INVITE_EMAIL,
            "role": "viewer",
        }, token=access_token, tenant_id=tenant_id)
        t.check("دعوة مكررة → 409", status2 == 409,
                f"got {status2}: {data2.get('detail', '')[:80]}")

    # ══════════════════════════════════════════
    # PHASE 7: GET /invites
    # ══════════════════════════════════════════
    t.set_phase("قائمة الدعوات (GET /invites)")

    status, data = api("GET", "/invites", token=access_token, tenant_id=tenant_id)

    t.check("Status = 200", status == 200, f"got {status}")
    if isinstance(data, list):
        t.check("يوجد دعوات (≥1)", len(data) >= 1, f"count={len(data)}")
        if data:
            inv = data[0]
            t.check("الدعوة تحتوي على email", "email" in inv, str(list(inv.keys())))
            t.check("الدعوة تحتوي على status", "status" in inv, inv.get("status", "?"))
            print(f"  📌 دعوات: {len(data)}")
            for i in data[:3]:
                print(f"      • {i.get('email')} — {i.get('status')} — {i.get('role')}")
    else:
        t.check("يوجد دعوات (≥1)", False, f"type={type(data).__name__}")

    # ══════════════════════════════════════════
    # PHASE 8: DELETE /invites/:id (Revoke Invite)
    # ══════════════════════════════════════════
    t.set_phase("إلغاء دعوة (DELETE /invites/:id)")

    if invite_id:
        status, data = api("DELETE", f"/invites/{invite_id}",
                          token=access_token, tenant_id=tenant_id)
        t.check("Status = 204 No Content", status == 204, f"got {status}")

        # Verify it's revoked
        status2, data2 = api("GET", "/invites", token=access_token, tenant_id=tenant_id)
        if isinstance(data2, list):
            revoked = [i for i in data2 if i.get("id") == invite_id]
            if revoked:
                t.check("الدعوة الملغاة status = revoked",
                        revoked[0].get("status") == "revoked",
                        revoked[0].get("status", "?"))
            else:
                t.check("الدعوة الملغاة status = revoked", True, "deleted from list")
    else:
        t.check("Status = 204 No Content", False, "no invite_id")

    # ══════════════════════════════════════════
    # PHASE 9: DELETE /tenants/current/members/:id (Remove Member)
    # ══════════════════════════════════════════
    t.set_phase("إزالة عضو (DELETE /tenants/current/members/:id)")

    if created_user_id:
        # ── 9a: Cannot remove self ──
        status, data = api("DELETE", f"/tenants/current/members/{user_id}",
                          token=access_token, tenant_id=tenant_id)
        t.check("إزالة النفس → 400", status == 400,
                f"got {status}: {data.get('detail', '')[:80]}")

        # ── 9b: Remove created user ──
        status, data = api("DELETE", f"/tenants/current/members/{created_user_id}",
                          token=access_token, tenant_id=tenant_id)
        t.check("إزالة عضو → 204", status == 204, f"got {status}")

        # ── 9c: Verify member removed ──
        status3, data3 = api("GET", "/tenants/current/members",
                            token=access_token, tenant_id=tenant_id)
        if isinstance(data3, list):
            still_there = any(m.get("user_id") == created_user_id for m in data3)
            t.check("العضو لم يعد في القائمة", not still_there,
                    f"still present" if still_there else "confirmed removed")
        else:
            t.check("العضو لم يعد في القائمة", False, "list fetch failed")

        # ── 9d: Remove non-existent → 404 ──
        status4, data4 = api("DELETE", f"/tenants/current/members/{created_user_id}",
                            token=access_token, tenant_id=tenant_id)
        t.check("إزالة عضو غير موجود → 404", status4 == 404,
                f"got {status4}: {data4.get('detail', '')[:80]}")
    else:
        for label in ["إزالة النفس → 400", "إزالة عضو → 204",
                      "العضو لم يعد في القائمة", "إزالة عضو غير موجود → 404"]:
            t.check(label, False, "no created_user_id")

    # ══════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════
    all_passed = t.print_summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
