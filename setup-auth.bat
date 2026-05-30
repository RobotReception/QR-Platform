@echo off
REM ============================================================
REM نظام إدارة القوالب - إعداد المصادقة
REM ============================================================

cls
echo.
echo ========================================
echo    نظام اداره القوالب - اعداد المصادقة
echo ========================================
echo.
echo جاري التحضير...
echo.

REM الخطوة 1: إنشاء Token وحفظ البيانات
python << 'PYTHON_EOF'
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import text
from jose import jwt
from datetime import datetime, timedelta
import json

async def setup():
    async with AsyncSessionLocal() as db:
        # Get owner user from first tenant
        result = await db.execute(text("""
            SELECT t.id as tenant_id, m.user_id
            FROM tenants t
            LEFT JOIN memberships m ON t.id = m.tenant_id
            WHERE m.status = 'active' AND m.role = 'owner'
            LIMIT 1
        """))

        row = result.mappings().first()
        if not row:
            print("[ERROR] No owner found in database")
            return False

        tenant_id = str(row['tenant_id'])
        user_id = str(row['user_id'])

        JWT_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"

        payload = {
            "sub": user_id,
            "email": "owner@example.com",
            "aud": "authenticated",
            "role": "authenticated",
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp()),
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        # Save to file for reference
        auth_data = {
            "access_token": token,
            "tenant_id": tenant_id,
            "user_id": user_id
        }

        with open('auth-data.json', 'w', encoding='utf-8') as f:
            json.dump(auth_data, f, indent=2)

        print("[SUCCESS] Authentication data ready")
        print(f"[INFO] Access Token: {token[:50]}...")
        print(f"[INFO] Tenant ID: {tenant_id}")
        print(f"[INFO] User ID: {user_id}")
        print(f"[INFO] Data saved to: auth-data.json")

        return True

try:
    success = asyncio.run(setup())
    if not success:
        exit(1)
except Exception as e:
    print(f"[ERROR] {str(e)}")
    exit(1)
PYTHON_EOF

if errorlevel 1 goto error

echo.
echo ========================================
echo    خطوات الاستخدام
echo ========================================
echo.
echo 1. افتح المتصفح: http://localhost:5173
echo 2. اضغط F12 لفتح Developer Tools
echo 3. انسخ واحد من الخيارات التالية:
echo.
echo الخيار 1 - الطريقة السريعة (انسخ هذا):
echo ========================================
echo.

python << 'PYTHON_EOF'
import json
try:
    with open('auth-data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    code = f"""localStorage.setItem('qentry_access_token', '{data['access_token']}');
localStorage.setItem('qentry_tenant_id', '{data['tenant_id']}');
localStorage.setItem('qentry_user', '{data['user_id']}');
location.reload();"""
    print(code)
except:
    print("Error reading auth data")
PYTHON_EOF

echo.
echo ========================================
echo.
echo 4. الصق في Console ثم اضغط Enter
echo 5. سيتم إعادة تحميل الصفحة تلقائياً
echo.
echo ========================================
echo    تم بنجاح!
echo ========================================
echo.
echo الآن يجب أن تتمكن من:
echo  - عرض القوالب
echo  - معاينة القوالب
echo  - تحميل الصور
echo  - حذف القوالب
echo.
echo للدعم، راجع: GETTING_ACCESS.md
echo.
pause
goto end

:error
echo.
echo [ERROR] Failed to setup authentication
echo Please check that:
echo  1. Backend is running (http://127.0.0.1:8000)
echo  2. Database is accessible
echo  3. Python dependencies are installed
echo.
pause

:end
