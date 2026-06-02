import asyncio
import os
import sys
import asyncpg

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

async def main():
    print("=" * 60)
    print("  Executing Migration V10 via raw asyncpg (Local)")
    print("=" * 60)
    
    settings = get_settings()
    # Convert sqlalchemy db url to asyncpg compatible format
    db_url = settings.database_url
    if "postgresql+asyncpg://" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
    print(f"Connecting to database...")
    try:
        conn = await asyncpg.connect(db_url)
        print("Connected successfully")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    migration_path = os.path.join("supabase", "migration_v10_registration_forms.sql")
    if not os.path.exists(migration_path):
        print(f"Migration file not found at: {migration_path}")
        await conn.close()
        return
        
    with open(migration_path, "r", encoding="utf-8") as f:
        sql_content = f.read()
        
    print("Executing SQL file...")
    try:
        async with conn.transaction():
            await conn.execute(sql_content)
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Execution failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
