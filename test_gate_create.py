"""Direct test: simulate gate creation endpoint logic."""
import sys, asyncio
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')

async def test():
    from app.database import get_db
    from sqlalchemy import text

    async for db in get_db():
        # 1. Get first event and its tenant
        r = await db.execute(text("""
            SELECT e.id, e.tenant_id, m.user_id
            FROM events e
            JOIN memberships m ON m.tenant_id = e.tenant_id
            WHERE m.role = 'owner' AND m.status = 'active'
            LIMIT 1
        """))
        row = r.mappings().first()
        if not row:
            print("No events found!")
            return
        
        event_id = str(row['id'])
        tenant_id = str(row['tenant_id'])
        user_id = str(row['user_id'])
        print(f"event_id: {event_id[:8]}...")
        print(f"tenant_id: {tenant_id[:8]}...")
        print(f"user_id: {user_id[:8]}...")

        # 2. Test user_has_permission
        try:
            r2 = await db.execute(
                text("SELECT public.user_has_permission(CAST(:tid AS uuid), CAST(:uid AS uuid), :pkey)"),
                {"tid": tenant_id, "uid": user_id, "pkey": "gates.manage"}
            )
            has_perm = r2.scalar()
            print(f"\nhas gates.manage permission: {has_perm}")
        except Exception as e:
            print(f"\nuser_has_permission ERROR: {e}")

        # 3. Test actual gate INSERT
        print("\nTesting gate INSERT with string_to_array fix...")
        try:
            classes_str = "vip,normal"
            r3 = await db.execute(
                text("""
                    INSERT INTO event_gates (event_id, name, name_ar, allowed_classes)
                    VALUES (
                        :eid, :name, :name_ar,
                        string_to_array(:classes, ',')::ticket_class[]
                    )
                    RETURNING *
                """),
                {
                    "eid": event_id,
                    "name": "بوابة الاختبار",
                    "name_ar": "Test Gate",
                    "classes": classes_str
                }
            )
            gate_row = r3.mappings().first()
            print(f"Gate INSERT OK!")
            print(f"  id: {gate_row['id']}")
            print(f"  name: {gate_row['name']}")
            print(f"  allowed_classes: {gate_row['allowed_classes']}")
            await db.rollback()  # Don't keep the test gate
        except Exception as e:
            print(f"Gate INSERT ERROR: {e}")
            await db.rollback()

        break

asyncio.run(test())
