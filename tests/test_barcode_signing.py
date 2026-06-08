"""Tests for the HMAC signing used to sign invitation barcodes."""
import app.services.barcode_service as bc
from app.config import Settings


def test_sign_with_key_is_deterministic_and_128_bit():
    key = b"unit-test-key"
    sig1 = bc._sign_with_key("invite-1", "token-1", key)
    sig2 = bc._sign_with_key("invite-1", "token-1", key)
    assert sig1 == sig2
    # 16 bytes => 32 hex chars (128-bit strength)
    assert len(sig1) == 32


def test_sign_with_key_changes_with_input():
    key = b"unit-test-key"
    base = bc._sign_with_key("invite-1", "token-1", key)
    assert bc._sign_with_key("invite-1", "token-2", key) != base
    assert bc._sign_with_key("invite-2", "token-1", key) != base


def test_verify_signature_accepts_valid_and_rejects_tampered(monkeypatch):
    monkeypatch.setattr(
        bc, "settings", Settings(invite_hmac_secret="a" * 64, app_env="production")
    )
    sig = bc.sign_payload("invite-1", "token-1")
    assert bc.verify_signature("invite-1", "token-1", sig) is True
    # Wrong signature
    assert bc.verify_signature("invite-1", "token-1", "deadbeef" * 4) is False
    # Tampered token
    assert bc.verify_signature("invite-1", "other-token", sig) is False


def test_verify_signature_supports_key_rotation(monkeypatch):
    old_key = "old" * 22  # 66 chars
    monkeypatch.setattr(
        bc, "settings", Settings(invite_hmac_secret=old_key, app_env="production")
    )
    sig_signed_with_old = bc.sign_payload("invite-1", "token-1")

    # Rotate: new primary key, old key moved to *_prev
    monkeypatch.setattr(
        bc,
        "settings",
        Settings(
            invite_hmac_secret="new" * 22,
            invite_hmac_secret_prev=old_key,
            app_env="production",
        ),
    )
    # Old signature still validates during the grace period
    assert bc.verify_signature("invite-1", "token-1", sig_signed_with_old) is True
