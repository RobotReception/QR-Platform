"""Shared pytest configuration.

Environment variables are set here BEFORE any application module is imported,
because ``app.config.get_settings`` is cached with ``lru_cache`` and reads the
environment exactly once. These values are dummies that let the app be imported
and exercised without a live database or Supabase project.
"""
import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/testdb",
)
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "INVITE_HMAC_SECRET",
    "0" * 64,  # 64 hex chars — dummy signing key for tests only
)
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-not-real")
