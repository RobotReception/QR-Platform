"""
Middleware for:
1. Tenant Resolution (header → subdomain → custom domain → JWT)
2. Tenant Status Enforcement (suspended/cancelled blocks access)
3. Security Headers
4. Rate Limiting (basic)
"""
import time
import logging
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy import text

from app.tenant_context import set_current_tenant, clear_current_tenant
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Paths that don't require tenant resolution
TENANT_EXEMPT_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/signup",
    "/api/v1/auth/login",
    "/api/v1/auth/password-reset/send-otp",
    "/api/v1/auth/password-reset/verify-otp",
    "/api/v1/auth/password-reset/confirm-new",
    "/api/v1/auth/refresh",
    "/api/v1/auth/me",
    "/api/v1/plans",
    "/api/v1/invites/accept",
    "/api/v1/webhooks/stripe",
    "/api/v1/tenants",
    "/api/v1/platform",
}

# Subdomains to ignore
SYSTEM_SUBDOMAINS = {"www", "api", "app", "admin", "mail", "smtp", "ftp", "localhost"}


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """
    Resolves the current tenant from each request using multiple strategies:
    Priority 1: X-Tenant-ID or X-Tenant-Slug header
    Priority 2: Subdomain (e.g., amal.system.com → slug=amal)
    Priority 3: Custom domain lookup (e.g., app.amal.com)
    
    After resolution, validates tenant status (active/trial only).
    Stores tenant in contextvars for the duration of the request.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip tenant resolution for exempt paths
        path = request.url.path
        print(f"TenantResolutionMiddleware: path={path}, is_exempt={path.startswith('/api/v1/templates/fonts/file/')}", flush=True)
        if any(path.startswith(p) for p in TENANT_EXEMPT_PATHS) or path.startswith("/api/v1/templates/fonts/file/"):
            response = await call_next(request)
            return response

        tenant = None
        async with AsyncSessionLocal() as db:
            # Strategy 1: Header (X-Tenant-ID or X-Tenant-Slug)
            tenant_id = request.headers.get("X-Tenant-ID")
            tenant_slug = request.headers.get("X-Tenant-Slug")

            if tenant_id:
                result = await db.execute(
                    text("SELECT id, slug, name, status, plan FROM tenants WHERE id = :id"),
                    {"id": tenant_id},
                )
                tenant = result.mappings().first()

            elif tenant_slug:
                result = await db.execute(
                    text("SELECT id, slug, name, status, plan FROM tenants WHERE slug = :slug"),
                    {"slug": tenant_slug},
                )
                tenant = result.mappings().first()

            # Strategy 2: Subdomain
            if not tenant:
                host = request.headers.get("host", "")
                parts = host.split(".")
                if len(parts) >= 3:
                    subdomain = parts[0].lower()
                    if subdomain not in SYSTEM_SUBDOMAINS:
                        result = await db.execute(
                            text("SELECT id, slug, name, status, plan FROM tenants WHERE slug = :slug AND status IN ('active', 'trial')"),
                            {"slug": subdomain},
                        )
                        tenant = result.mappings().first()

            # Strategy 3: Custom domain
            if not tenant:
                host = request.headers.get("host", "").split(":")[0]
                if host and host not in ("localhost", "127.0.0.1", "0.0.0.0"):
                    result = await db.execute(
                        text("""
                            SELECT t.id, t.slug, t.name, t.status, t.plan
                            FROM tenant_domains td
                            JOIN tenants t ON t.id = td.tenant_id
                            WHERE td.domain = :domain AND td.is_verified = true
                        """),
                        {"domain": host},
                    )
                    tenant = result.mappings().first()

        # If no tenant found for a tenant-required path
        if not tenant:
            return JSONResponse(
                status_code=400,
                content={"detail": "لم يتم تحديد المستأجر. أرسل X-Tenant-ID أو X-Tenant-Slug في الهيدر."},
            )

        # Enforce tenant status
        tenant_dict = dict(tenant)
        if tenant_dict["status"] not in ("active", "trial"):
            status_messages = {
                "suspended": "حساب المستأجر معلّق. يرجى التواصل مع الدعم.",
                "cancelled": "حساب المستأجر ملغى.",
                "deleted": "حساب المستأجر محذوف.",
            }
            return JSONResponse(
                status_code=403,
                content={"detail": status_messages.get(tenant_dict["status"], "حساب المستأجر غير نشط.")},
            )

        # Set tenant in context
        set_current_tenant(tenant_dict)

        try:
            response = await call_next(request)
            return response
        finally:
            clear_current_tenant()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory rate limiting per IP with tiered limits.

    Three tiers:
      1. Public endpoints (view/rsvp): 30/min — brute-force prevention (no auth)
      2. Check-in scan: 300/min + burst 20/3s — high-throughput gate ops (JWT required)
      3. Everything else: 120/min — general protection

    For production use Redis-backed rate limiting.
    """

    # Public endpoints: truly unauthenticated, strict limit
    PUBLIC_PREFIXES = (
        "/api/v1/invitations/view/",   # public: view by token (no auth)
        "/api/v1/invitations/rsvp/",   # public: RSVP by token (no auth)
    )

    # Check-in: authenticated (JWT + checkin.scan), high-throughput at gates
    CHECKIN_PREFIXES = (
        "/api/v1/checkin/scan",
    )

    def __init__(
        self,
        app,
        requests_per_minute: int = 120,
        public_per_minute: int = 30,
        checkin_per_minute: int = 300,
        checkin_burst_max: int = 20,
        checkin_burst_window: float = 3.0,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.public_per_minute = public_per_minute
        self.checkin_per_minute = checkin_per_minute
        self.checkin_burst_max = checkin_burst_max
        self.checkin_burst_window = checkin_burst_window
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._public_requests: dict[str, list[float]] = defaultdict(list)
        self._checkin_requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60.0
        path = request.url.path

        # Tier 1: Public endpoints (30/min) — brute-force prevention
        is_public = any(path.startswith(p) for p in self.PUBLIC_PREFIXES)
        if is_public:
            self._public_requests[client_ip] = [
                t for t in self._public_requests[client_ip] if now - t < window
            ]
            if len(self._public_requests[client_ip]) >= self.public_per_minute:
                logger.warning("Public rate limit hit: IP=%s path=%s", client_ip, path)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "تم تجاوز حد الطلبات. حاول مرة أخرى بعد دقيقة."},
                    headers={"Retry-After": "60"},
                )
            self._public_requests[client_ip].append(now)

        # Tier 2: Check-in (300/min + burst 20/3s) — high-throughput gate ops
        # Rate limit key: ip + user_id (from JWT) to avoid NAT collisions at venues
        is_checkin = any(path.startswith(p) for p in self.CHECKIN_PREFIXES)
        if is_checkin:
            # Extract user_id from Authorization header for composite key
            auth_header = request.headers.get("authorization", "")
            user_hint = auth_header[-12:] if len(auth_header) > 12 else ""
            checkin_key = f"{client_ip}:{user_hint}"

            self._checkin_requests[checkin_key] = [
                t for t in self._checkin_requests[checkin_key] if now - t < window
            ]
            # Per-minute limit
            if len(self._checkin_requests[checkin_key]) >= self.checkin_per_minute:
                logger.warning("Check-in rate limit hit: key=%s", checkin_key)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "تم تجاوز حد طلبات تسجيل الدخول."},
                    headers={"Retry-After": "10"},
                )
            # Burst protection (20 requests in 3 seconds)
            recent_burst = [t for t in self._checkin_requests[checkin_key] if now - t < self.checkin_burst_window]
            if len(recent_burst) >= self.checkin_burst_max:
                logger.warning("Check-in burst limit hit: key=%s (%d in %.0fs)", checkin_key, len(recent_burst), self.checkin_burst_window)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "طلبات سريعة جداً. انتظر لحظات."},
                    headers={"Retry-After": "3"},
                )
            self._checkin_requests[checkin_key].append(now)

        # Tier 3: Global rate limit (120/min)
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < window
        ]

        if len(self._requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "تم تجاوز حد الطلبات. حاول مرة أخرى بعد قليل."},
                headers={"Retry-After": "60"},
            )

        self._requests[client_ip].append(now)
        response = await call_next(request)
        return response
