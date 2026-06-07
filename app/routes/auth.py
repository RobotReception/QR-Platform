from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

from app.auth import get_current_user, get_tenant_id_from_header, CurrentUser
from app.config import get_settings
from app.database import get_db, get_supabase_admin
from app.services.email_service import (
    send_password_reset_email,
    send_password_changed_email,
    send_welcome_email,
    send_email_verification,
    send_otp_email,
)
from app.services.audit_service import log_audit
from app.services.permission_service import get_user_tenants_with_roles, get_user_permissions
from app.services.provisioning_service import provision_tenant_manual
import asyncio
import re
import secrets
import random
import string
from datetime import datetime, timedelta, timezone

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ══════════════════════════════════════════════
# Request / Response Models
# ══════════════════════════════════════════════

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    organization_name: Optional[str] = None  # Auto-generated if not provided


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None  # Optional: select tenant on login


class SelectTenantRequest(BaseModel):
    tenant_id: str


class SendOtpRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp_code: str


class ConfirmNewPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class TenantInfo(BaseModel):
    tenant_id: UUID
    slug: str
    name: str
    tenant_status: str
    plan: str
    role: str
    membership_status: str


class AuthResponse(BaseModel):
    message: str
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    tenants: Optional[list[TenantInfo]] = None
    requires_tenant_selection: bool = False


class OtpResponse(BaseModel):
    message: str
    email: Optional[str] = None
    reset_token: Optional[str] = None
    remaining_attempts: Optional[int] = None
    blocked_until: Optional[str] = None


# ══════════════════════════════════════════════
# SIGNUP
# ══════════════════════════════════════════════

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user via Supabase Auth, auto-create tenant and profile."""
    from app.database import get_supabase_client
    supabase = get_supabase_client()

    # ── 1. Create Supabase user ──
    try:
        result = await asyncio.to_thread(
            supabase.auth.sign_up,
            {
                "email": body.email,
                "password": body.password,
                "options": {
                    "data": {"full_name": body.full_name or ""}
                }
            },
        )
        user = result.user
    except Exception as e:
        error_msg = str(e)
        if "already" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(status_code=409, detail="البريد الإلكتروني مسجل مسبقاً")
        raise HTTPException(status_code=400, detail=f"فشل التسجيل: {error_msg}")

    user_id = str(user.id)

    # ── 2. Auto-create tenant ──
    org_name = body.organization_name or f"{body.full_name or body.email.split('@')[0]}'s Workspace"
    base_slug = re.sub(r'[^a-z0-9]+', '-', org_name.lower()).strip('-')
    if len(base_slug) < 3:
        base_slug = f"org-{base_slug}"
    slug = f"{base_slug[:40]}-{secrets.token_hex(3)}"

    try:
        # Create tenant
        tenant_result = await db.execute(
            text("""
                INSERT INTO tenants (slug, name, created_by, metadata)
                VALUES (:slug, :name, :created_by, '{}'::jsonb)
                RETURNING id, slug, name, status, plan, created_at
            """),
            {"slug": slug, "name": org_name, "created_by": user_id},
        )
        tenant = tenant_result.mappings().first()
        tenant_id = str(tenant["id"])

        # ── 3. Create owner membership ──
        await db.execute(
            text("""
                INSERT INTO memberships (tenant_id, user_id, role, status)
                VALUES (:tid, :uid, 'owner', 'active')
            """),
            {"tid": tenant_id, "uid": user_id},
        )

        # ── 4. Create free subscription ──
        await db.execute(
            text("""
                INSERT INTO subscriptions (tenant_id, plan_id, status,
                    current_period_start, current_period_end, trial_ends_at)
                VALUES (
                    :tid,
                    (SELECT id FROM plans WHERE code = 'starter'),
                    'active', now(), now() + INTERVAL '30 days',
                    now() + INTERVAL '14 days'
                )
            """),
            {"tid": tenant_id},
        )

        # ── 5. Provision default roles, permissions, settings ──
        await provision_tenant_manual(db, tenant["id"], user.id)

        # ── 6. Create user profile ──
        await db.execute(
            text("""
                INSERT INTO profiles (id, full_name, avatar_url)
                VALUES (:uid, :name, '')
                ON CONFLICT (id) DO NOTHING
            """),
            {"uid": user_id, "name": body.full_name or ""},
        )

        await db.commit()

        tenant_info = [TenantInfo(
            tenant_id=tenant["id"],
            slug=tenant["slug"],
            name=tenant["name"],
            tenant_status=tenant["status"],
            plan=tenant["plan"],
            role="owner",
            membership_status="active",
        )]
    except Exception as e:
        await db.rollback()
        import logging
        logging.getLogger(__name__).error(f"Failed to provision tenant for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Tenant provisioning failed: {str(e)}")

    # ── 7. Generate email verification link ──
    try:
        link_response = await asyncio.to_thread(
            supabase.auth.admin.generate_link,
            {"type": "signup", "email": body.email},
        )
        verify_link = getattr(link_response, "properties", {})
        action_link = verify_link.action_link if hasattr(verify_link, "action_link") else f"{settings.app_url}/auth/verify"
    except Exception:
        action_link = f"{settings.app_url}/auth/verify"

    # ── 8. Send emails in background ──
    background_tasks.add_task(send_email_verification, body.email, action_link)
    background_tasks.add_task(send_welcome_email, body.email, body.full_name or "")

    return AuthResponse(
        message="تم التسجيل بنجاح. يرجى تأكيد بريدك الإلكتروني.",
        user_id=user_id,
        tenants=tenant_info,
    )


# ══════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════

@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password via Supabase Auth.
    If user belongs to multiple tenants, returns tenant list for selection.
    """
    from app.database import get_supabase_client
    supabase = get_supabase_client()  # Use anon key for sign_in

    try:
        result = await asyncio.to_thread(
            supabase.auth.sign_in_with_password,
            {"email": body.email, "password": body.password},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="بيانات الدخول غير صحيحة",
        )

    user_id = str(result.user.id)

    # Update last_login_at (skip if profiles table doesn't exist)
    try:
        await db.execute(
            text("UPDATE profiles SET last_login_at = now() WHERE id = :uid"),
            {"uid": user_id},
        )
        await db.commit()
    except Exception:
        pass  # Skip if profiles table not set up yet

    # Get user's tenants (skip if not set up)
    try:
        tenants = await get_user_tenants_with_roles(db, UUID(user_id))
        active_tenants = [t for t in tenants if t["tenant_status"] in ("active", "trial")]
    except Exception:
        active_tenants = []  # No tenants if schema not ready

    if len(active_tenants) > 1 and not body.tenant_id:
        # Multiple tenants — require selection
        return AuthResponse(
            message="يرجى اختيار المستأجر",
            user_id=user_id,
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
            tenants=[TenantInfo(**t) for t in active_tenants],
            requires_tenant_selection=True,
        )

    return AuthResponse(
        message="تم تسجيل الدخول بنجاح",
        user_id=user_id,
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        tenants=[TenantInfo(**t) for t in active_tenants] if active_tenants else None,
    )


# ══════════════════════════════════════════════
# PASSWORD RESET — STEP 1: SEND OTP
# ══════════════════════════════════════════════

def _generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP code."""
    return ''.join(random.choices(string.digits, k=length))


@router.post("/password-reset/send-otp", response_model=OtpResponse)
async def send_otp(
    body: SendOtpRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1: Verify email exists in the system, then send an OTP code.
    - Checks if the email is registered in Supabase Auth
    - Checks for active blocks (too many failed attempts)
    - Generates a 6-digit OTP valid for 10 minutes
    - Sends it via email
    """
    supabase = get_supabase_admin()
    email = body.email.lower().strip()

    # ── 1. Check if email exists in Supabase Auth ──
    try:
        users_response = supabase.auth.admin.list_users()
        user_exists = any(
            u.email and u.email.lower() == email
            for u in users_response
        )
    except Exception:
        # Fallback: try direct DB query
        try:
            result = await db.execute(
                text("SELECT id FROM auth.users WHERE email = :email"),
                {"email": email},
            )
            user_exists = result.first() is not None
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="حدث خطأ في التحقق من البريد الإلكتروني",
            )

    if not user_exists:
        raise HTTPException(
            status_code=404,
            detail="البريد الإلكتروني غير مسجل في النظام",
        )

    # ── 2. Check for active blocks ──
    block_result = await db.execute(
        text("""
            SELECT blocked_until FROM password_reset_otps
            WHERE email = :email
              AND blocked_until IS NOT NULL
              AND blocked_until > now()
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"email": email},
    )
    block_row = block_result.mappings().first()
    if block_row:
        raise HTTPException(
            status_code=429,
            detail="تم تجاوز عدد المحاولات المسموحة. يرجى المحاولة بعد 15 دقيقة.",
        )

    # ── 3. Invalidate any previous unused OTPs for this email ──
    await db.execute(
        text("""
            UPDATE password_reset_otps
            SET expires_at = now()
            WHERE email = :email
              AND is_verified = FALSE
              AND expires_at > now()
        """),
        {"email": email},
    )

    # ── 4. Generate and store OTP ──
    otp_code = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    await db.execute(
        text("""
            INSERT INTO password_reset_otps (email, otp_code, expires_at)
            VALUES (:email, :otp_code, :expires_at)
        """),
        {"email": email, "otp_code": otp_code, "expires_at": expires_at},
    )
    await db.commit()

    # ── 5. Send OTP email in background ──
    background_tasks.add_task(send_otp_email, email, otp_code)

    return OtpResponse(
        message="تم إرسال رمز التحقق إلى بريدك الإلكتروني",
        email=email,
    )


# ══════════════════════════════════════════════
# PASSWORD RESET — STEP 2: VERIFY OTP
# ══════════════════════════════════════════════

@router.post("/password-reset/verify-otp", response_model=OtpResponse)
async def verify_otp(
    body: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Verify the OTP code.
    - 3 attempts max, then block for 15 minutes
    - On success, returns a unique reset_token for step 3
    """
    email = body.email.lower().strip()
    otp_code = body.otp_code.strip()

    # ── 1. Check for active blocks ──
    block_result = await db.execute(
        text("""
            SELECT blocked_until FROM password_reset_otps
            WHERE email = :email
              AND blocked_until IS NOT NULL
              AND blocked_until > now()
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"email": email},
    )
    if block_result.mappings().first():
        raise HTTPException(
            status_code=429,
            detail="تم تجاوز عدد المحاولات المسموحة. يرجى المحاولة بعد 15 دقيقة.",
        )

    # ── 2. Find latest valid OTP ──
    otp_result = await db.execute(
        text("""
            SELECT id, otp_code, attempts, max_attempts
            FROM password_reset_otps
            WHERE email = :email
              AND is_verified = FALSE
              AND expires_at > now()
              AND blocked_until IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"email": email},
    )
    otp_row = otp_result.mappings().first()

    if not otp_row:
        raise HTTPException(
            status_code=400,
            detail="لا يوجد رمز تحقق صالح. يرجى طلب رمز جديد.",
        )

    # ── 3. Check OTP match ──
    if otp_row["otp_code"] != otp_code:
        new_attempts = otp_row["attempts"] + 1
        remaining = otp_row["max_attempts"] - new_attempts

        if remaining <= 0:
            # Block for 15 minutes
            blocked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            await db.execute(
                text("""
                    UPDATE password_reset_otps
                    SET attempts = :attempts, blocked_until = :blocked_until
                    WHERE id = :id
                """),
                {
                    "attempts": new_attempts,
                    "blocked_until": blocked_until,
                    "id": otp_row["id"],
                },
            )
            await db.commit()
            raise HTTPException(
                status_code=429,
                detail="تم تجاوز عدد المحاولات المسموحة. تم حظرك لمدة 15 دقيقة.",
            )
        else:
            await db.execute(
                text("UPDATE password_reset_otps SET attempts = :attempts WHERE id = :id"),
                {"attempts": new_attempts, "id": otp_row["id"]},
            )
            await db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"رمز التحقق غير صحيح. لديك {remaining} محاولة متبقية.",
            )

    # ── 4. OTP is correct — generate reset_token ──
    reset_token = secrets.token_urlsafe(48)

    await db.execute(
        text("""
            UPDATE password_reset_otps
            SET is_verified = TRUE, reset_token = :reset_token
            WHERE id = :id
        """),
        {"reset_token": reset_token, "id": otp_row["id"]},
    )
    await db.commit()

    return OtpResponse(
        message="تم التحقق بنجاح",
        reset_token=reset_token,
    )


# ══════════════════════════════════════════════
# PASSWORD RESET — STEP 3: SET NEW PASSWORD
# ══════════════════════════════════════════════

@router.post("/password-reset/confirm-new", response_model=OtpResponse)
async def confirm_new_password(
    body: ConfirmNewPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Set new password using the reset_token from step 2.
    - Validates the reset_token is valid and not expired
    - Changes the password via Supabase Admin API
    - Invalidates all OTPs for this email
    """
    supabase = get_supabase_admin()

    # ── 1. Find the verified OTP record by reset_token ──
    token_result = await db.execute(
        text("""
            SELECT id, email FROM password_reset_otps
            WHERE reset_token = :reset_token
              AND is_verified = TRUE
              AND expires_at > now()
            LIMIT 1
        """),
        {"reset_token": body.reset_token},
    )
    token_row = token_result.mappings().first()

    if not token_row:
        raise HTTPException(
            status_code=400,
            detail="رمز غير صالح أو منتهي الصلاحية. يرجى إعادة العملية.",
        )

    email = token_row["email"]

    # ── 2. Find the user in Supabase and update password ──
    try:
        users_response = supabase.auth.admin.list_users()
        user = None
        for u in users_response:
            if u.email and u.email.lower() == email.lower():
                user = u
                break

        if not user:
            # Fallback: try direct DB query
            result = await db.execute(
                text("SELECT id FROM auth.users WHERE email = :email"),
                {"email": email},
            )
            user_row = result.mappings().first()
            if not user_row:
                raise HTTPException(status_code=400, detail="المستخدم غير موجود")
            user_id = str(user_row["id"])
        else:
            user_id = str(user.id)

        # Update password
        supabase.auth.admin.update_user_by_id(
            user_id,
            {"password": body.new_password},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="فشل تغيير كلمة المرور. يرجى المحاولة مرة أخرى.",
        )

    # ── 3. Invalidate all OTPs for this email ──
    await db.execute(
        text("""
            UPDATE password_reset_otps
            SET expires_at = now(), reset_token = NULL
            WHERE email = :email
        """),
        {"email": email},
    )

    # ── 4. Audit log ──
    await log_audit(
        db,
        tenant_id=None,
        actor_user_id=UUID(user_id),
        action="auth.password_reset_otp",
        resource_type="user",
        resource_id=user_id,
    )
    await db.commit()

    # ── 5. Send confirmation email ──
    background_tasks.add_task(send_password_changed_email, email)

    return OtpResponse(
        message="تم تغيير كلمة المرور بنجاح. يمكنك تسجيل الدخول الآن.",
    )


# ══════════════════════════════════════════════
# CHANGE PASSWORD (authenticated user)
# ══════════════════════════════════════════════

@router.post("/change-password", response_model=AuthResponse)
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the currently authenticated user."""
    supabase = get_supabase_admin()

    # Verify current password by attempting sign-in
    if not user.email:
        raise HTTPException(status_code=400, detail="لا يمكن تحديد البريد الإلكتروني من التوكن")

    try:
        await asyncio.to_thread(
            supabase.auth.sign_in_with_password,
            {"email": user.email, "password": body.current_password},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="كلمة المرور الحالية غير صحيحة",
        )

    # Update password
    try:
        await asyncio.to_thread(
            supabase.auth.admin.update_user_by_id,
            str(user.id),
            {"password": body.new_password},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"فشل تغيير كلمة المرور: {str(e)}")

    # Send confirmation email
    background_tasks.add_task(send_password_changed_email, user.email)

    # Audit log
    await log_audit(
        db,
        tenant_id=None,
        actor_user_id=user.id,
        action="auth.password_change",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return AuthResponse(
        message="تم تغيير كلمة المرور بنجاح",
        user_id=str(user.id),
    )


# ══════════════════════════════════════════════
# REFRESH TOKEN
# ══════════════════════════════════════════════

class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(body: RefreshRequest):
    """Refresh the access token using a refresh token."""
    supabase = get_supabase_admin()

    try:
        result = await asyncio.to_thread(supabase.auth.refresh_session, body.refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رمز التحديث غير صالح أو منتهي الصلاحية",
        )

    return AuthResponse(
        message="تم تحديث التوكن بنجاح",
        user_id=str(result.user.id),
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
    )


# ══════════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════════

@router.post("/logout", response_model=AuthResponse)
async def logout(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout — sign out from Supabase (invalidates refresh token)."""
    supabase = get_supabase_admin()

    try:
        # Sign out via admin API
        await asyncio.to_thread(supabase.auth.admin.sign_out, str(user.id))
    except Exception:
        pass  # Best effort — token will expire naturally

    await log_audit(
        db, tenant_id=None, actor_user_id=user.id,
        action="auth.logout", resource_type="user", resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return AuthResponse(message="تم تسجيل الخروج بنجاح")


# ══════════════════════════════════════════════
# GET CURRENT USER INFO (enhanced)
# ══════════════════════════════════════════════

@router.get("/me")
async def get_me(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user info + profile + list of tenants with roles.
    When X-Tenant-ID header is set, includes permissions for that tenant.
    This is the main endpoint the frontend calls after login.
    """
    # Get profile (graceful fallback if DB unavailable)
    profile = None
    try:
        profile_result = await db.execute(
            text("""
                SELECT full_name, avatar_url, phone, is_staff, status,
                       email_verified_at::text, last_login_at::text,
                       created_at::text
                FROM profiles WHERE id = :uid
            """),
            {"uid": str(user.id)},
        )
        profile = profile_result.mappings().first()
    except Exception:
        pass  # DB unavailable, use JWT data only

    # Get tenants with roles (graceful fallback if not set up)
    tenants = []
    try:
        tenants = await get_user_tenants_with_roles(db, user.id)
    except Exception:
        pass  # No tenants if schema not ready

    permissions: list[str] = []
    try:
        tenant_id = get_tenant_id_from_header(request)
        permissions = await get_user_permissions(db, tenant_id, user.id)
    except Exception:
        pass

    return {
        "user_id": str(user.id),
        "email": user.email,
        "full_name": profile["full_name"] if profile else None,
        "avatar_url": profile["avatar_url"] if profile else None,
        "phone": profile["phone"] if profile else None,
        "is_staff": profile["is_staff"] if profile else False,
        "status": profile["status"] if profile else "active",
        "email_verified_at": profile["email_verified_at"] if profile else None,
        "last_login_at": profile["last_login_at"] if profile else None,
        "created_at": profile["created_at"] if profile else None,
        "tenants": [TenantInfo(**t) for t in tenants],
        "permissions": permissions,
    }
