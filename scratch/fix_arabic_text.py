import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

sys.stdout.reconfigure(encoding="utf-8")

# Define the plans with correct Arabic values
PLANS_DATA = [
    {
        "code": "starter",
        "description": "للتجربة والاستخدام الشخصي",
        "subtitle": "ابدأ مجاناً"
    },
    {
        "code": "basic",
        "description": "للمؤسسات الصغيرة والاحتياجات الأساسية",
        "subtitle": "الأكثر اقتصاداً"
    },
    {
        "code": "pro",
        "description": "للأحداث والفعاليات المتوسطة والاحترافية",
        "subtitle": "الأكثر شعبية"
    },
    {
        "code": "business",
        "description": "للشركات ومنظمي الفعاليات الكبيرة",
        "subtitle": "للاحتياجات المتقدمة"
    },
    {
        "code": "enterprise",
        "description": "للمؤسسات الكبرى والجهات الحكومية",
        "subtitle": "حلول مخصصة بالكامل"
    }
]

# Define the addons with correct Arabic values
ADDONS_DATA = [
    {
        "key": "events_per_month",
        "label_ar": "أحداث شهرية",
        "unit_ar": "حدث",
        "icon": "📅"
    },
    {
        "key": "invitations_per_event",
        "label_ar": "دعوات لكل حدث",
        "unit_ar": "دعوة",
        "icon": "✉️"
    },
    {
        "key": "invitations_per_month",
        "label_ar": "دعوات شهرية",
        "unit_ar": "دعوة",
        "icon": "📨"
    },
    {
        "key": "gates_per_event",
        "label_ar": "بوابات لكل حدث",
        "unit_ar": "بوابة",
        "icon": "🚪"
    },
    {
        "key": "guests_max",
        "label_ar": "سعة الضيوف القصوى",
        "unit_ar": "ضيف",
        "icon": "👥"
    },
    {
        "key": "teams_max",
        "label_ar": "فرق العمل",
        "unit_ar": "فريق",
        "icon": "👔"
    },
    {
        "key": "team_members_per_team",
        "label_ar": "أعضاء لكل فريق",
        "unit_ar": "عضو",
        "icon": "👤"
    },
    {
        "key": "seats_max",
        "label_ar": "مستخدمو لوحة التحكم",
        "unit_ar": "مستخدم",
        "icon": "🖥️"
    },
    {
        "key": "designed_templates",
        "label_ar": "قوالب مصممة",
        "unit_ar": "قالب",
        "icon": "🎨"
    },
    {
        "key": "registration_forms_max",
        "label_ar": "نماذج التسجيل",
        "unit_ar": "نموذج",
        "icon": "📋"
    },
    {
        "key": "storage_mb",
        "label_ar": "مساحة التخزين",
        "unit_ar": "GB",
        "icon": "💾"
    },
    {
        "key": "messages_per_month",
        "label_ar": "رسائل شهرية",
        "unit_ar": "رسالة",
        "icon": "💬"
    },
    {
        "key": "ai_requests_per_month",
        "label_ar": "طلبات AI شهرية",
        "unit_ar": "طلب",
        "icon": "🤖"
    }
]

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    
    async with engine.begin() as conn:
        print("1. Updating plans Arabic text...")
        for plan in PLANS_DATA:
            res = await conn.execute(
                text("UPDATE plans SET description = :desc, subtitle = :sub WHERE code = :code"),
                {"desc": plan["description"], "sub": plan["subtitle"], "code": plan["code"]}
            )
            print(f"   - Plan {plan['code']}: {res.rowcount} rows updated")
            
        print("\n2. Updating plan addons Arabic text...")
        for addon in ADDONS_DATA:
            res = await conn.execute(
                text("UPDATE plan_addons SET label_ar = :lbl, unit_ar = :unit, icon = :icon WHERE key = :key"),
                {"lbl": addon["label_ar"], "unit": addon["unit_ar"], "icon": addon["icon"], "key": addon["key"]}
            )
            print(f"   - Addon {addon['key']}: {res.rowcount} rows updated")

        print("\nChecking the updated values:")
        res = await conn.execute(text("SELECT key, label_ar, icon FROM plan_addons"))
        for row in res.mappings():
            print(f"   - {row['key']}: icon={row['icon']}, label={row['label_ar']}")

asyncio.run(main())
