"""
Symmetric encryption for short-lived secrets at rest (e.g. a pending org-request
applicant's password, which must be recoverable once — at approval — to create
the Supabase user, then wiped).

Uses Fernet with a key derived from `supabase_jwt_secret`, so no new secret needs
to be added to the environment.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    secret = settings.supabase_jwt_secret or "dev-insecure-fallback-secret-change-me"
    # Derive a 32-byte urlsafe-base64 key deterministically from the JWT secret.
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a string; returns urlsafe ciphertext token."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Decrypt a token produced by encrypt_secret. Raises ValueError on failure."""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as e:
        raise ValueError("failed to decrypt secret") from e
