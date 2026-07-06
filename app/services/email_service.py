import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _smtp_is_configured() -> bool:
    """Treat placeholder local-development credentials as disabled."""
    smtp_user = (settings.smtp_user or "").strip()
    smtp_pass = (settings.smtp_pass or "").strip()

    if not smtp_user or not smtp_pass:
        return False

    disabled_values = {"disabled", "changeme", "change-me", "example", "localhost"}
    if smtp_pass.lower() in disabled_values:
        return False
    if smtp_user.lower().endswith("@localhost"):
        return False

    return True


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    plain_body: Optional[str] = None,
) -> bool:
    """Send an email via SMTP. Returns True on success."""
    if not _smtp_is_configured():
        logger.info("SMTP not configured for delivery; skipping email to %s", to_email)
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.smtp_sender_name} <{settings.smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = settings.smtp_admin_email or settings.smtp_user

    if plain_body:
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.sendmail(settings.smtp_user, to_email, msg.as_string())
        logger.info("Email sent to %s: %s", to_email, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, str(e))
        return False


# ══════════════════════════════════════════════
# Pre-built email senders
# ══════════════════════════════════════════════

def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    """Send password reset email."""
    subject = "إعادة تعيين كلمة المرور - Qr Platform"
    html = _build_email(
        template="password_reset",
        icon_svg=_ICON_LOCK,
        icon_bg="#fef2f2",
        icon_color="#ef4444",
        preheader="لقد تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بحسابك",
        heading="إعادة تعيين كلمة المرور",
        paragraphs=[
            "لقد تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بحسابك على <strong>Qr Platform</strong>.",
            "اضغط على الزر أدناه لإنشاء كلمة مرور جديدة. الرابط صالح لمدة <strong>ساعة واحدة</strong> فقط.",
        ],
        button_text="إعادة تعيين كلمة المرور",
        button_url=reset_link,
        button_bg="#ef4444",
        info_items=[
            ("الجهاز", "متصفح الويب"),
            ("صلاحية الرابط", "ساعة واحدة"),
        ],
        warning_text="إذا لم تطلب إعادة تعيين كلمة المرور، يمكنك تجاهل هذا البريد بأمان. لن يتم إجراء أي تغيير على حسابك.",
        plain_link=reset_link,
    )
    plain = f"إعادة تعيين كلمة المرور\n\nاضغط على الرابط التالي:\n{reset_link}\n\nالرابط صالح لمدة ساعة واحدة."
    return send_email(to_email, subject, html, plain)


def send_invite_email(to_email: str, invite_link: str, tenant_name: str, inviter_name: str) -> bool:
    """Send team invite email."""
    subject = f"دعوة للانضمام إلى {tenant_name} - Qr Platform"
    html = _build_email(
        template="invite",
        icon_svg=_ICON_USERS,
        icon_bg="#eff6ff",
        icon_color="#3b82f6",
        preheader=f"قام {inviter_name} بدعوتك للانضمام إلى {tenant_name}",
        heading=f"دعوة للانضمام إلى {tenant_name}",
        paragraphs=[
            f"قام <strong>{inviter_name}</strong> بدعوتك للانضمام إلى فريق <strong>{tenant_name}</strong> على Qr Platform.",
            "اضغط على الزر أدناه لقبول الدعوة والانضمام إلى الفريق.",
        ],
        button_text="قبول الدعوة",
        button_url=invite_link,
        button_bg="#3b82f6",
        info_items=[
            ("الفريق", tenant_name),
            ("الداعي", inviter_name),
            ("صلاحية الدعوة", "7 أيام"),
        ],
        warning_text="إذا لم تكن تتوقع هذه الدعوة، يمكنك تجاهل هذا البريد بأمان.",
        plain_link=invite_link,
    )
    plain = f"دعوة للانضمام إلى {tenant_name}\n\nقام {inviter_name} بدعوتك.\nاضغط على الرابط: {invite_link}\n\nالدعوة صالحة لمدة 7 أيام."
    return send_email(to_email, subject, html, plain)


def send_welcome_email(to_email: str, full_name: str) -> bool:
    """Send welcome email after signup."""
    name = full_name or "بك"
    subject = "مرحباً بك في Qr Platform!"
    dashboard_url = f"{settings.app_url}/dashboard"
    html = _build_email(
        template="welcome",
        icon_svg=_ICON_ROCKET,
        icon_bg="#f0fdf4",
        icon_color="#22c55e",
        preheader=f"مرحباً {name}! حسابك جاهز على Qr Platform",
        heading=f"أهلاً {name}!",
        paragraphs=[
            "شكراً لتسجيلك في <strong>Qr Platform</strong>. حسابك جاهز الآن!",
            "يمكنك البدء بإنشاء مساحة عمل جديدة، دعوة فريقك، والاستفادة من جميع المميزات.",
        ],
        button_text="ابدأ الآن",
        button_url=dashboard_url,
        button_bg="#22c55e",
        features=[
            ("إنشاء مساحة عمل", "أنشئ مساحة عمل خاصة بفريقك أو مشروعك"),
            ("دعوة الفريق", "أضف أعضاء فريقك بسهولة عبر البريد الإلكتروني"),
            ("إدارة الاشتراكات", "اختر الباقة المناسبة لاحتياجاتك"),
        ],
        warning_text=None,
        plain_link=dashboard_url,
    )
    plain = f"مرحباً {name}!\n\nشكراً لتسجيلك في Qr Platform.\nابدأ من هنا: {dashboard_url}"
    return send_email(to_email, subject, html, plain)


def send_org_request_received(to_email: str, full_name: str, org_name: str) -> bool:
    """Acknowledge an organizer-team registration request."""
    name = full_name or "بك"
    subject = "تم استلام طلب التسجيل - Qr Platform"
    html = _build_email(
        template="org_request_received",
        icon_svg=_ICON_USERS,
        icon_bg="#eff6ff",
        icon_color="#3b82f6",
        preheader="استلمنا طلب تسجيل فريق التنظيم الخاص بك وهو قيد المراجعة",
        heading=f"شكراً {name}!",
        paragraphs=[
            f"استلمنا طلب تسجيل <strong>{org_name}</strong> كفريق تنظيم على <strong>Qr Platform</strong>.",
            "سيقوم فريق المنصة بمراجعة طلبك، وستصلك رسالة عند الموافقة لتتمكن من تسجيل الدخول.",
        ],
        button_text="زيارة المنصة",
        button_url=settings.app_url,
        button_bg="#3b82f6",
        warning_text="لا حاجة لأي إجراء الآن. سنخبرك فور اكتمال المراجعة.",
        plain_link=settings.app_url,
    )
    plain = f"شكراً {name}!\n\nاستلمنا طلب تسجيل {org_name} كفريق تنظيم. طلبك قيد المراجعة وسنخبرك عند الموافقة."
    return send_email(to_email, subject, html, plain)


def send_org_request_approved(to_email: str, full_name: str, org_name: str) -> bool:
    """Notify an applicant that their organizer-team request was approved."""
    name = full_name or "بك"
    subject = "تمت الموافقة على طلبك - Qr Platform"
    login_url = f"{settings.app_url}/auth/login"
    html = _build_email(
        template="org_request_approved",
        icon_svg=_ICON_ROCKET,
        icon_bg="#f0fdf4",
        icon_color="#22c55e",
        preheader=f"تمت الموافقة على {org_name}! يمكنك تسجيل الدخول الآن",
        heading=f"مبارك {name}!",
        paragraphs=[
            f"تمت الموافقة على تسجيل <strong>{org_name}</strong> كفريق تنظيم على <strong>Qr Platform</strong>.",
            "تم تجهيز مساحة العمل الخاصة بك. يمكنك الآن تسجيل الدخول بنفس البريد وكلمة المرور اللذين استخدمتهما في الطلب.",
        ],
        button_text="تسجيل الدخول",
        button_url=login_url,
        button_bg="#22c55e",
        plain_link=login_url,
    )
    plain = f"مبارك {name}!\n\nتمت الموافقة على {org_name}. سجّل الدخول الآن: {login_url}"
    return send_email(to_email, subject, html, plain)


def send_org_request_rejected(to_email: str, full_name: str, org_name: str, reason: str = "") -> bool:
    """Notify an applicant that their organizer-team request was rejected."""
    name = full_name or "بك"
    subject = "بخصوص طلب التسجيل - Qr Platform"
    paragraphs = [
        f"نشكرك على اهتمامك بالتسجيل بـ <strong>{org_name}</strong> على <strong>Qr Platform</strong>.",
        "بعد المراجعة، لم نتمكن من الموافقة على الطلب في الوقت الحالي.",
    ]
    if reason:
        paragraphs.append(f"السبب: {reason}")
    html = _build_email(
        template="org_request_rejected",
        icon_svg=_ICON_SHIELD,
        icon_bg="#fef2f2",
        icon_color="#ef4444",
        preheader="تحديث بخصوص طلب تسجيل فريق التنظيم",
        heading=f"عزيزي {name}",
        paragraphs=paragraphs,
        button_text="التواصل مع الدعم",
        button_url=settings.app_url,
        button_bg="#6366f1",
        warning_text="يمكنك التواصل معنا لمزيد من التفاصيل أو إعادة التقديم لاحقاً.",
        plain_link=settings.app_url,
    )
    plain = f"عزيزي {name}،\n\nلم نتمكن من الموافقة على طلب {org_name} حالياً."
    if reason:
        plain += f"\nالسبب: {reason}"
    return send_email(to_email, subject, html, plain)


def send_password_changed_email(to_email: str) -> bool:
    """Send confirmation that password was changed."""
    subject = "تم تغيير كلمة المرور - Qr Platform"
    login_url = f"{settings.app_url}/login"
    html = _build_email(
        template="password_changed",
        icon_svg=_ICON_SHIELD,
        icon_bg="#f0fdf4",
        icon_color="#22c55e",
        preheader="تم تغيير كلمة المرور الخاصة بحسابك بنجاح",
        heading="تم تغيير كلمة المرور بنجاح",
        paragraphs=[
            "تم تغيير كلمة المرور الخاصة بحسابك على <strong>Qr Platform</strong> بنجاح.",
            "يمكنك الآن تسجيل الدخول باستخدام كلمة المرور الجديدة.",
        ],
        button_text="تسجيل الدخول",
        button_url=login_url,
        button_bg="#6366f1",
        info_items=None,
        warning_text="إذا لم تقم بهذا التغيير، يرجى التواصل مع فريق الدعم فوراً لتأمين حسابك.",
        warning_critical=True,
        plain_link=login_url,
    )
    plain = f"تم تغيير كلمة المرور بنجاح.\n\nإذا لم تقم بهذا التغيير، يرجى التواصل مع الدعم فوراً.\n\nتسجيل الدخول: {login_url}"
    return send_email(to_email, subject, html, plain)


def send_email_verification(to_email: str, verify_link: str) -> bool:
    """Send email verification link."""
    subject = "تأكيد البريد الإلكتروني - Qr Platform"
    html = _build_email(
        template="verify",
        icon_svg=_ICON_MAIL,
        icon_bg="#faf5ff",
        icon_color="#a855f7",
        preheader="يرجى تأكيد بريدك الإلكتروني لإكمال التسجيل",
        heading="تأكيد بريدك الإلكتروني",
        paragraphs=[
            "شكراً لتسجيلك في <strong>Qr Platform</strong>!",
            "يرجى تأكيد بريدك الإلكتروني بالضغط على الزر أدناه لتفعيل حسابك بالكامل.",
        ],
        button_text="تأكيد البريد الإلكتروني",
        button_url=verify_link,
        button_bg="#a855f7",
        info_items=None,
        warning_text="إذا لم تقم بإنشاء حساب على Qr Platform، يمكنك تجاهل هذا البريد بأمان.",
        plain_link=verify_link,
    )
    plain = f"تأكيد البريد الإلكتروني\n\nاضغط على الرابط التالي لتأكيد بريدك:\n{verify_link}"
    return send_email(to_email, subject, html, plain)


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """Send OTP code for password reset."""
    subject = "رمز التحقق - Qr Platform"
    html = _build_email(
        template="otp",
        icon_svg=_ICON_LOCK,
        icon_bg="#faf5ff",
        icon_color="#a855f7",
        preheader=f"رمز التحقق الخاص بك: {otp_code}",
        heading="رمز التحقق",
        paragraphs=[
            "لقد تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بحسابك على <strong>Qr Platform</strong>.",
            "استخدم الرمز التالي لإكمال عملية إعادة التعيين:",
        ],
        button_text=otp_code,
        button_url="#",
        button_bg="#6366f1",
        info_items=[
            ("صلاحية الرمز", "10 دقائق"),
            ("عدد المحاولات", "3 محاولات"),
        ],
        warning_text="إذا لم تطلب إعادة تعيين كلمة المرور، يمكنك تجاهل هذا البريد بأمان. لن يتم إجراء أي تغيير على حسابك.",
        plain_link=None,
        otp_code=otp_code,
    )
    plain = f"رمز التحقق الخاص بك: {otp_code}\n\nالرمز صالح لمدة 10 دقائق فقط.\n\nإذا لم تطلب هذا الرمز، تجاهل هذا البريد."
    return send_email(to_email, subject, html, plain)


def send_subscription_upgraded_email(to_email: str, plan_name: str, full_name: str = "") -> bool:
    """Send subscription upgrade confirmation."""
    name = full_name or "العميل"
    subject = f"تم ترقية اشتراكك إلى {plan_name} - Qr Platform"
    dashboard_url = f"{settings.app_url}/dashboard"
    html = _build_email(
        template="subscription",
        icon_svg=_ICON_STAR,
        icon_bg="#fffbeb",
        icon_color="#f59e0b",
        preheader=f"تم ترقية اشتراكك إلى باقة {plan_name}",
        heading=f"تم ترقية اشتراكك إلى {plan_name}!",
        paragraphs=[
            f"مرحباً <strong>{name}</strong>،",
            f"تم ترقية اشتراكك بنجاح إلى باقة <strong>{plan_name}</strong>. يمكنك الآن الاستفادة من جميع المميزات الجديدة.",
        ],
        button_text="استعرض المميزات",
        button_url=dashboard_url,
        button_bg="#f59e0b",
        info_items=[
            ("الباقة الجديدة", plan_name),
        ],
        warning_text=None,
        plain_link=dashboard_url,
    )
    plain = f"تم ترقية اشتراكك إلى {plan_name}.\n\nاستعرض المميزات: {dashboard_url}"
    return send_email(to_email, subject, html, plain)


# ══════════════════════════════════════════════
# SVG Icons (inline, email-safe)
# ══════════════════════════════════════════════

_ICON_LOCK = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>'

_ICON_USERS = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'

_ICON_ROCKET = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>'

_ICON_SHIELD = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>'

_ICON_MAIL = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>'

_ICON_STAR = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a.53.53 0 0 0 .4.29l5.16.754a.53.53 0 0 1 .294.904l-3.733 3.638a.53.53 0 0 0-.152.469l.882 5.14a.53.53 0 0 1-.77.56l-4.614-2.426a.53.53 0 0 0-.494 0L7.14 18.73a.53.53 0 0 1-.77-.56l.882-5.14a.53.53 0 0 0-.152-.47L3.367 8.922a.53.53 0 0 1 .294-.904l5.16-.754a.53.53 0 0 0 .4-.29z"/></svg>'


# ══════════════════════════════════════════════
# Master HTML Template Builder
# ══════════════════════════════════════════════

def _build_email(
    *,
    template: str,
    icon_svg: str,
    icon_bg: str,
    icon_color: str,
    preheader: str,
    heading: str,
    paragraphs: list[str],
    button_text: str,
    button_url: str,
    button_bg: str,
    info_items: Optional[list[tuple[str, str]]] = None,
    features: Optional[list[tuple[str, str]]] = None,
    warning_text: Optional[str] = None,
    warning_critical: bool = False,
    plain_link: Optional[str] = None,
    otp_code: Optional[str] = None,
) -> str:
    """Build a complete, responsive, RTL HTML email."""

    # Info box rows
    info_html = ""
    if info_items:
        rows = ""
        for label, value in info_items:
            rows += f"""
                <tr>
                    <td style="padding:8px 16px;color:#6b7280;font-size:13px;border-bottom:1px solid #f3f4f6;white-space:nowrap;">{label}</td>
                    <td style="padding:8px 16px;color:#1f2937;font-size:13px;font-weight:600;border-bottom:1px solid #f3f4f6;text-align:left;">{value}</td>
                </tr>"""
        info_html = f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f9fafb;border-radius:8px;margin:0 0 24px;border:1px solid #f3f4f6;">
                {rows}
            </table>"""

    # Features list (for welcome email)
    features_html = ""
    if features:
        items = ""
        for feat_title, feat_desc in features:
            items += f"""
                <tr>
                    <td style="padding:12px 16px;border-bottom:1px solid #f3f4f6;">
                        <p style="margin:0 0 2px;color:#1f2937;font-size:14px;font-weight:600;">{feat_title}</p>
                        <p style="margin:0;color:#6b7280;font-size:13px;">{feat_desc}</p>
                    </td>
                </tr>"""
        features_html = f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f9fafb;border-radius:8px;margin:0 0 24px;border:1px solid #f3f4f6;">
                {items}
            </table>"""

    # Warning box
    warning_html = ""
    if warning_text:
        w_bg = "#fef2f2" if warning_critical else "#fffbeb"
        w_border = "#fecaca" if warning_critical else "#fde68a"
        w_icon_color = "#ef4444" if warning_critical else "#f59e0b"
        w_text_color = "#991b1b" if warning_critical else "#92400e"
        w_icon = "&#9888;" if warning_critical else "&#128712;"
        warning_html = f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
                <tr>
                    <td style="background-color:{w_bg};border:1px solid {w_border};border-radius:8px;padding:14px 18px;">
                        <p style="margin:0;color:{w_text_color};font-size:13px;line-height:1.7;">
                            <span style="color:{w_icon_color};font-size:16px;margin-left:6px;">{w_icon}</span>
                            {warning_text}
                        </p>
                    </td>
                </tr>
            </table>"""

    # Paragraphs
    paragraphs_html = ""
    for p in paragraphs:
        paragraphs_html += f'<p style="margin:0 0 16px;color:#374151;font-size:15px;line-height:1.8;">{p}</p>'

    # Plain link fallback
    plain_link_html = ""
    if plain_link:
        plain_link_html = f"""
            <p style="margin:24px 0 0;color:#9ca3af;font-size:12px;line-height:1.6;word-break:break-all;">
                إذا لم يعمل الزر، انسخ الرابط التالي في متصفحك:<br>
                <a href="{plain_link}" style="color:#6366f1;text-decoration:underline;">{plain_link}</a>
            </p>"""

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="color-scheme" content="light">
    <meta name="supported-color-schemes" content="light">
    <title>{heading}</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:'Segoe UI',Tahoma,Geneva,Verdana,Arial,sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;">
    <!-- Preheader (hidden preview text) -->
    <div style="display:none;font-size:1px;color:#f3f4f6;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">
        {preheader}
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f3f4f6;">
        <tr>
            <td align="center" style="padding:32px 16px;">

                <!-- Logo -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;margin-bottom:24px;">
                    <tr>
                        <td align="center" style="padding:0 0 8px;">
                            <h1 style="margin:0;font-size:28px;font-weight:800;color:#6366f1;letter-spacing:-0.5px;">
                                Qr Platform
                            </h1>
                        </td>
                    </tr>
                </table>

                <!-- Main Card -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08),0 4px 24px rgba(0,0,0,0.04);">

                    <!-- Icon + Heading -->
                    <tr>
                        <td style="padding:40px 40px 0;" align="center">
                            <div style="width:64px;height:64px;border-radius:16px;background-color:{icon_bg};display:inline-block;text-align:center;line-height:64px;margin-bottom:24px;">
                                <span style="color:{icon_color};vertical-align:middle;">{icon_svg}</span>
                            </div>
                            <h2 style="margin:0 0 8px;color:#111827;font-size:22px;font-weight:700;line-height:1.4;">{heading}</h2>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:20px 40px 0;">
                            {paragraphs_html}
                        </td>
                    </tr>

                    <!-- Button or OTP Code -->
                    <tr>
                        <td style="padding:8px 40px 24px;" align="center">
                            {f'''
                            <div style="background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);border-radius:16px;padding:28px 20px;margin:8px 0;text-align:center;">
                                <p style="margin:0 0 8px;color:rgba(255,255,255,0.7);font-size:13px;">رمز التحقق الخاص بك</p>
                                <p style="margin:0;font-size:38px;font-weight:800;letter-spacing:12px;color:#ffffff;font-family:monospace;direction:ltr;">{otp_code}</p>
                            </div>
                            ''' if otp_code else f'''
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="border-radius:10px;background-color:{button_bg};">
                                        <a href="{button_url}" target="_blank" style="display:inline-block;padding:14px 40px;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;border-radius:10px;letter-spacing:0.3px;mso-padding-alt:0;text-underline-color:#ffffff;">
                                            <!--[if mso]><i style="mso-font-width:150%;mso-text-raise:30px;" hidden>&nbsp;</i><![endif]-->
                                            <span style="mso-text-raise:15px;">{button_text}</span>
                                            <!--[if mso]><i style="mso-font-width:150%;" hidden>&nbsp;</i><![endif]-->
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            '''}
                        </td>
                    </tr>

                    <!-- Info Box -->
                    {"<tr><td style='padding:0 40px 8px;'>" + info_html + "</td></tr>" if info_html else ""}

                    <!-- Features List -->
                    {"<tr><td style='padding:0 40px 8px;'>" + features_html + "</td></tr>" if features_html else ""}

                    <!-- Warning -->
                    {"<tr><td style='padding:0 40px 8px;'>" + warning_html + "</td></tr>" if warning_html else ""}

                    <!-- Plain Link Fallback -->
                    <tr>
                        <td style="padding:0 40px 32px;">
                            {plain_link_html}
                        </td>
                    </tr>

                </table>

                <!-- Footer -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;margin-top:24px;">
                    <tr>
                        <td align="center" style="padding:0 40px;">
                            <p style="margin:0 0 8px;color:#9ca3af;font-size:12px;line-height:1.6;">
                                &copy; 2026 Qr Platform. جميع الحقوق محفوظة.
                            </p>
                            <p style="margin:0;color:#d1d5db;font-size:11px;">
                                هذا البريد مرسل من <a href="{settings.app_url}" style="color:#9ca3af;text-decoration:underline;">Qr Platform</a>
                                &nbsp;&bull;&nbsp;
                                <a href="{settings.app_url}/settings/notifications" style="color:#9ca3af;text-decoration:underline;">إدارة الإشعارات</a>
                            </p>
                        </td>
                    </tr>
                </table>

            </td>
        </tr>
    </table>
</body>
</html>"""
