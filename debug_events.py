"""Debug script: check events table schema and test API call."""
import asyncio
import sys
sys.path.insert(0, 'd:/QR')

async def test():
    from app.database import get_db
    from sqlalchemy import text
    
    async for db in get_db():
        # 1. Check if events table exists
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM events"))
            count = result.scalar()
            print(f"[OK] events table exists, rows: {count}")
        except Exception as e:
            print(f"[ERR] events table: {e}")
        
        # 2. Get column names
        try:
            result = await db.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='events' "
                "ORDER BY ordinal_position"
            ))
            rows = result.fetchall()
            print(f"[OK] columns ({len(rows)}):", [r[0] for r in rows])
            
            # Check specifically for deleted_at
            col_names = [r[0] for r in rows]
            if 'deleted_at' in col_names:
                print("[OK] deleted_at column EXISTS")
            else:
                print("[MISS] deleted_at column MISSING - need migration!")
                
        except Exception as e:
            print(f"[ERR] schema query: {e}")
        
        # 3. Check event_categories
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM event_categories"))
            count = result.scalar()
            print(f"[OK] event_categories table, rows: {count}")
        except Exception as e:
            print(f"[ERR] event_categories: {e}")
        
        # 4. Check event_gates
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM event_gates"))
            count = result.scalar()
            print(f"[OK] event_gates table, rows: {count}")
        except Exception as e:
            print(f"[ERR] event_gates: {e}")
        
        # 5. Check ticket_class enum
        try:
            result = await db.execute(text(
                "SELECT enumlabel FROM pg_enum e "
                "JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = 'ticket_class'"
            ))
            vals = [r[0] for r in result.fetchall()]
            print(f"[OK] ticket_class enum: {vals}")
        except Exception as e:
            print(f"[ERR] ticket_class enum: {e}")
        
        # 6. Try raw SELECT with deleted_at filter
        try:
            result = await db.execute(text(
                "SELECT id, title, status FROM events "
                "WHERE tenant_id = '00000000-0000-0000-0000-000000000000' "
                "AND deleted_at IS NULL LIMIT 1"
            ))
            print(f"[OK] deleted_at query works fine")
        except Exception as e:
            print(f"[ERR] deleted_at query: {e}")
        
        break

asyncio.run(test())
