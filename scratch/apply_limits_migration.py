import asyncio
import sys
from sqlalchemy import text
from app.database import AsyncSessionLocal

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    print("Applying Migration v15: Standard Plan Limits and Features...")
    
    with open("supabase/migration_v15_standard_plan_limits.sql", "r", encoding="utf-8") as f:
        sql = f.read()
        
    async with AsyncSessionLocal() as db:
        # Split by semicolon to run each statement separately
        statements = sql.split(";")
        for stmt in statements:
            stmt_clean = stmt.strip()
            if not stmt_clean:
                continue
            if stmt_clean.upper() in ("BEGIN", "COMMIT", "BEGIN;", "COMMIT;"):
                continue
            await db.execute(text(stmt_clean))
        await db.commit()
        
    print("SUCCESS: Limits migration applied successfully!")

if __name__ == "__main__":
    asyncio.run(main())
