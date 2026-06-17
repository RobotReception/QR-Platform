import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, tenants, invites, subscriptions, usage, profiles, audit, platform, roles, dashboard
from app.routes import events, digital_invitations, guests, templates, teams, checkin, batches, fast_invitations, registration_forms
from app.config import get_settings
from app.middleware import TenantResolutionMiddleware, SecurityHeadersMiddleware, RateLimitMiddleware


def _configure_console_encoding() -> None:
    """Avoid cp1252 logging crashes on Windows when Arabic text is emitted."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_configure_console_encoding()
settings = get_settings()

logging.basicConfig(
    level=logging.INFO if settings.is_production else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Fail fast on insecure/incomplete production configuration ──
_config_problems = settings.validate_for_production()
if _config_problems:
    for _p in _config_problems:
        logger.critical("Production config error: %s", _p)
    raise RuntimeError(
        "Refusing to start in production with invalid configuration: "
        + "; ".join(_config_problems)
    )

allowed_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip()
]

app = FastAPI(
    title="SaaS Core API",
    description="Multi-tenant SaaS backend with Supabase Auth, RBAC, Billing, and Usage Tracking",
    version="2.0.0",
    # Hide interactive API docs in production.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# ── Middleware (order matters: last added = first executed) ──
app.add_middleware(TenantResolutionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──
app.include_router(auth.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(invites.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(usage.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")
app.include_router(platform.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")

# ── Digital Invitations Platform ──
app.include_router(events.router, prefix="/api/v1")
app.include_router(digital_invitations.router, prefix="/api/v1")
app.include_router(guests.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(checkin.router, prefix="/api/v1")
app.include_router(batches.router, prefix="/api/v1")
app.include_router(fast_invitations.router, prefix="/api/v1")
app.include_router(registration_forms.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting API (env=%s, rate-limit backend=%s)", settings.app_env, _rate_backend())
    try:
        from app.services import storage_service
        await storage_service.ensure_bucket_exists()
    except Exception as e:
        logger.warning("Could not ensure bucket exists on startup: %s", e)


def _rate_backend() -> str:
    try:
        from app.services.rate_limiter import rate_limiter
        return rate_limiter.backend
    except Exception:
        return "unknown"


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "digital-invitations", "version": "3.0.0"}
