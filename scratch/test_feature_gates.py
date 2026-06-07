import asyncio
import sys
import json
from uuid import uuid4
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.feature_service import check_feature_flag, get_plan_limit, require_feature
from fastapi import HTTPException

# Prevent Windows console encoding issues
sys.stdout.reconfigure(encoding="utf-8")

async def test():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("Testing Feature Gating & Plan Limits")
        print("=" * 60)

        # 1. Create a temporary tenant
        tenant_id = uuid4()
        tenant_name = f"Test Tenant {tenant_id.hex[:6]}"
        print(f"\n1. Creating test tenant: {tenant_name}")
        await db.execute(
            text("INSERT INTO tenants (id, name, slug, plan, status) VALUES (:id, :name, :slug, 'starter', 'active')"),
            {"id": tenant_id, "name": tenant_name, "slug": f"test-{tenant_id.hex[:6]}"}
        )
        await db.commit()

        # 2. Check Starter plan features
        print("\n2. Checking Starter Plan features (Default: no RSVP, no WhatsApp, no PDF export, no AI)...")
        rsvp_ok = await check_feature_flag(db, tenant_id, "rsvp")
        wa_ok = await check_feature_flag(db, tenant_id, "whatsapp_delivery")
        pdf_ok = await check_feature_flag(db, tenant_id, "pdf_export")
        ai_ok = await check_feature_flag(db, tenant_id, "ai_features")
        email_ok = await check_feature_flag(db, tenant_id, "email_delivery")
        
        print(f"   Email Delivery (all plans): {email_ok} (Expected: True)")
        print(f"   RSVP: {rsvp_ok} (Expected: False)")
        print(f"   WhatsApp: {wa_ok} (Expected: False)")
        print(f"   PDF Export: {pdf_ok} (Expected: False)")
        print(f"   AI Features: {ai_ok} (Expected: False)")

        assert email_ok is True
        assert rsvp_ok is False
        assert wa_ok is False
        assert pdf_ok is False
        assert ai_ok is False
        print("   Starter Plan features verified successfully!")

        # 3. Check Starter limits
        print("\n3. Checking Starter limits...")
        forms_limit = await get_plan_limit(db, tenant_id, "registration_forms_max")
        events_limit = await get_plan_limit(db, tenant_id, "events_per_month")
        designed_templates_limit = await get_plan_limit(db, tenant_id, "designed_templates")
        
        print(f"   registration_forms_max: {forms_limit} (Expected: 1)")
        print(f"   events_per_month: {events_limit} (Expected: 1)")
        print(f"   designed_templates: {designed_templates_limit} (Expected: 1)")

        assert forms_limit == 1
        assert events_limit == 1
        assert designed_templates_limit == 1
        print("   Starter limits verified successfully!")

        # 4. Check Pro plan features
        print("\n4. Updating tenant to Pro and verifying features...")
        await db.execute(
            text("UPDATE tenants SET plan = 'pro' WHERE id = :id"),
            {"id": tenant_id}
        )
        await db.commit()

        # Check Pro plan features
        rsvp_ok_pro = await check_feature_flag(db, tenant_id, "rsvp")
        wa_ok_pro = await check_feature_flag(db, tenant_id, "whatsapp_delivery")
        pdf_ok_pro = await check_feature_flag(db, tenant_id, "pdf_export")
        ai_ok_pro = await check_feature_flag(db, tenant_id, "ai_features")
        
        print(f"   Pro RSVP: {rsvp_ok_pro} (Expected: True)")
        print(f"   Pro WhatsApp: {wa_ok_pro} (Expected: True)")
        print(f"   Pro PDF Export: {pdf_ok_pro} (Expected: True)")
        print(f"   Pro AI Features: {ai_ok_pro} (Expected: True)")

        assert rsvp_ok_pro is True
        assert wa_ok_pro is True
        assert pdf_ok_pro is True
        assert ai_ok_pro is True

        forms_limit_pro = await get_plan_limit(db, tenant_id, "registration_forms_max")
        print(f"   Pro registration_forms_max: {forms_limit_pro} (Expected: 1)")
        assert forms_limit_pro == 1
        print("   Pro features and limits verified successfully!")

        # 5. Check Custom Plan limits overrides
        print("\n5. Creating an active Custom Plan for tenant and checking overrides...")
        plan_res = await db.execute(text("SELECT id FROM plans WHERE code = 'pro'"))
        pro_plan_id = plan_res.scalar()
        
        custom_limits = {
            "events_per_month": 12,
            "guests_max": 15000,
            "gates_per_event": 6,
            "seats_max": 30,
            "designed_templates": 15
        }
        
        await db.execute(
            text("""
                INSERT INTO custom_plans (tenant_id, base_plan_id, name, addons, base_price, addons_price, total_price_monthly, total_price_yearly, final_limits, status)
                VALUES (:tid, :base_id, 'My Custom Plan', CAST('{}' AS jsonb), 500, 100, 600, 6000, CAST(:limits AS jsonb), 'active')
            """),
            {"tid": tenant_id, "base_id": pro_plan_id, "limits": json.dumps(custom_limits)}
        )
        await db.commit()

        # Check limits after custom plan activation
        events_custom = await get_plan_limit(db, tenant_id, "events_per_month")
        seats_custom = await get_plan_limit(db, tenant_id, "seats_max")
        templates_custom = await get_plan_limit(db, tenant_id, "designed_templates")
        forms_custom = await get_plan_limit(db, tenant_id, "registration_forms_max")

        print(f"   Custom events_per_month: {events_custom} (Expected: 12)")
        print(f"   Custom seats_max: {seats_custom} (Expected: 30)")
        print(f"   Custom designed_templates: {templates_custom} (Expected: 15)")
        print(f"   Custom registration_forms_max (fallback): {forms_custom} (Expected: 1)")

        assert events_custom == 12
        assert seats_custom == 30
        assert templates_custom == 15
        assert forms_custom == 1
        print("   Custom Plan limit overrides verified successfully!")

        # Clean up
        print("\n6. Cleaning up test database records...")
        await db.execute(text("DELETE FROM custom_plans WHERE tenant_id = :tid"), {"tid": tenant_id})
        await db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tenant_id})
        await db.commit()
        print("   Cleanup done.")

        print("\n" + "=" * 60)
        print("All Feature Gating & Limits tests passed successfully!")
        print("=" * 60)

if __name__ == '__main__':
    asyncio.run(test())
