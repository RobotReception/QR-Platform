"""Unit tests for app.config.Settings — pure, no external services."""
import pytest

from app.config import Settings


def test_resolved_anon_key_prefers_anon():
    s = Settings(supabase_anon_key="anon", supabase_key="legacy")
    assert s.resolved_anon_key == "anon"


def test_resolved_anon_key_falls_back_to_legacy_key():
    s = Settings(supabase_anon_key="", supabase_key="legacy")
    assert s.resolved_anon_key == "legacy"


def test_resolved_hmac_key_uses_dedicated_secret():
    s = Settings(invite_hmac_secret="a" * 64)
    assert s.resolved_hmac_key == "a" * 64


def test_resolved_hmac_key_requires_secret_in_production():
    s = Settings(invite_hmac_secret="", app_env="production")
    with pytest.raises(ValueError):
        _ = s.resolved_hmac_key


def test_resolved_hmac_key_dev_fallback():
    s = Settings(invite_hmac_secret="", app_env="development", supabase_jwt_secret="jwt")
    # Falls back to JWT secret outside production
    assert s.resolved_hmac_key == "jwt"
