"""Migration: Add deleted_at column to events table for soft delete support."""
import asyncio
import sys
sys.path.insert(0, 'd:/QR')

async def migrate():
    from app.database import get_db
    from sqlalchemy import text
    
    async for db in get_db():
        try:
            # Check if column already exists
            result = await db.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='events' AND column_name='deleted_at'
            """))
            if result.first():
                print("[OK] deleted_at column already exists — no migration needed.")
                break
            
            print("[...] Adding deleted_at column to events table...")
            await db.execute(text("""
                ALTER TABLE events 
                ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL
            """))
            await db.commit()
            print("[OK] deleted_at column added successfully.")
            
            # Add index for performance
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_events_deleted_at 
                ON events(deleted_at) WHERE deleted_at IS NULL
            """))
            await db.commit()
            print("[OK] Index on deleted_at created.")
            
            # Verify
            result = await db.execute(text("SELECT COUNT(*) FROM events WHERE deleted_at IS NULL"))
            count = result.scalar()
            print(f"[OK] Verification: {count} active events (deleted_at IS NULL)")
            
        except Exception as e:
            await db.rollback()
            print(f"[ERR] Migration failed: {e}")
            raise
        break

asyncio.run(migrate())
