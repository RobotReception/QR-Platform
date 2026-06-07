from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_key: str = ""  # alias for supabase_anon_key
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Database
    database_url: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # PayPal
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_mode: str = "sandbox"

    # SMTP
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_admin_email: str = ""
    smtp_sender_name: str = "Qr Platform"

    # App
    app_url: str = "http://localhost:9000"
    app_env: str = "development"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    db_echo: bool = False

    # Worker (Celery + Redis)
    redis_url: str = "redis://localhost:6379/0"
    use_worker: bool = True  # False = fallback to BackgroundTask (dev only)

    # Storage
    storage_bucket: str = "invitations"  # Supabase Storage bucket name
    signed_url_expiry: int = 3600  # default signed URL expiry in seconds
    download_url_expiry: int = 86400 * 7  # batch download URL expiry (7 days)

    # Key rotation policy
    hmac_rotation_days: int = 90  # rotate INVITE_HMAC_SECRET every N days

    # Invitation Security (dedicated HMAC key, NOT reusing JWT secret)
    invite_hmac_secret: str = ""  # Primary signing key for barcodes
    invite_hmac_secret_prev: str = ""  # Previous key for rotation grace period

    @property
    def resolved_hmac_key(self) -> str:
        """Return the dedicated HMAC key used to sign invitation barcodes."""
        if self.invite_hmac_secret:
            return self.invite_hmac_secret
        if self.app_env.lower() == "production":
            raise ValueError("INVITE_HMAC_SECRET is required in production")
        return self.supabase_jwt_secret or "dev-only-change-me"

    @property
    def resolved_anon_key(self) -> str:
        """Return supabase_anon_key, falling back to supabase_key."""
        return self.supabase_anon_key or self.supabase_key

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
