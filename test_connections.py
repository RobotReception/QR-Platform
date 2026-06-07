"""
Test all connections: Backend API, Supabase, Database
"""
import requests
import socket
import sys

def check_port(host, port, name):
    """Check if a port is open."""
    try:
        s = socket.create_connection((host, port), timeout=3)
        s.close()
        print(f"  ✅ {name} (port {port}) — OPEN")
        return True
    except Exception as e:
        print(f"  ❌ {name} (port {port}) — CLOSED ({e})")
        return False

def check_http(url, name):
    """Check if an HTTP endpoint responds."""
    try:
        r = requests.get(url, timeout=5)
        print(f"  ✅ {name} — HTTP {r.status_code}: {r.text[:200]}")
        return True
    except requests.ConnectionError:
        print(f"  ❌ {name} — CONNECTION REFUSED (server not running)")
        return False
    except Exception as e:
        print(f"  ❌ {name} — ERROR: {e}")
        return False

def test_signup(base_url):
    """Test the signup endpoint."""
    try:
        r = requests.post(f"{base_url}/auth/signup", json={
            "email": "test_conn_check@example.com",
            "password": "TestPass123!",
            "full_name": "Test User",
            "organization_name": "Test Org"
        }, timeout=10)
        print(f"  📨 Signup Response — HTTP {r.status_code}: {r.text[:300]}")
        return r.status_code
    except requests.ConnectionError:
        print(f"  ❌ Signup — CONNECTION REFUSED (backend not running)")
        return None
    except Exception as e:
        print(f"  ❌ Signup — ERROR: {e}")
        return None

def test_supabase_auth(supabase_url, anon_key):
    """Test Supabase Auth directly."""
    try:
        headers = {
            "apikey": anon_key,
            "Content-Type": "application/json"
        }
        r = requests.post(f"{supabase_url}/auth/v1/signup", json={
            "email": "direct_test@example.com",
            "password": "TestPass123!"
        }, headers=headers, timeout=10)
        print(f"  📨 Supabase Auth Direct — HTTP {r.status_code}: {r.text[:300]}")
        return r.status_code
    except requests.ConnectionError:
        print(f"  ❌ Supabase Auth — CONNECTION REFUSED")
        return None
    except Exception as e:
        print(f"  ❌ Supabase Auth — ERROR: {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("  QR Platform — Connection Diagnostics")
    print("=" * 60)

    # 1. Port checks
    print("\n🔌 PORT CHECKS:")
    backend_ok = check_port("127.0.0.1", 8021, "Backend (FastAPI)")
    supabase_api_ok = check_port("127.0.0.1", 54821, "Supabase API")
    supabase_db_ok = check_port("127.0.0.1", 5434, "Supabase DB (PostgreSQL)")
    supabase_studio_ok = check_port("127.0.0.1", 54825, "Supabase Studio")
    frontend_ok = check_port("127.0.0.1", 5173, "Frontend (Vite)")

    # 2. HTTP checks
    print("\n🌐 HTTP ENDPOINT CHECKS:")
    if backend_ok:
        check_http("http://127.0.0.1:8021/health", "Backend /health")
        check_http("http://127.0.0.1:8021/docs", "Backend /docs")
    else:
        print("  ⏭️  Skipping backend HTTP checks (port closed)")

    if supabase_api_ok:
        check_http("http://127.0.0.1:54821/rest/v1/", "Supabase REST API")
    else:
        print("  ⏭️  Skipping Supabase HTTP checks (port closed)")

    # 3. Signup test
    print("\n📝 SIGNUP TEST:")
    if backend_ok:
        test_signup("http://127.0.0.1:8021/api/v1")
    else:
        print("  ⏭️  Skipping signup test (backend not running)")

    # 4. Direct Supabase Auth test
    print("\n🔐 DIRECT SUPABASE AUTH TEST:")
    anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
    if supabase_api_ok:
        test_supabase_auth("http://127.0.0.1:54821", anon_key)
    else:
        print("  ⏭️  Skipping Supabase auth test (API not running)")

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    issues = []
    if not backend_ok:
        issues.append("❌ Backend (FastAPI) is NOT running on port 8021")
    if not supabase_api_ok:
        issues.append("❌ Supabase API is NOT running on port 54821")
    if not supabase_db_ok:
        issues.append("❌ Supabase DB is NOT running on port 5434")
    if not frontend_ok:
        issues.append("❌ Frontend (Vite) is NOT running on port 5173")

    if issues:
        print("\n  ISSUES FOUND:")
        for issue in issues:
            print(f"    {issue}")
        print("\n  TO FIX:")
        if not supabase_db_ok or not supabase_api_ok:
            print("    1. cd d:\\QR\\supabase && npx supabase start")
        if not backend_ok:
            print("    2. cd d:\\QR && python -m uvicorn app.main:app --host 0.0.0.0 --port 8021 --reload")
        if not frontend_ok:
            print("    3. cd d:\\QR\\frontend && npm run dev")
    else:
        print("\n  ✅ All services are running!")
    print()
