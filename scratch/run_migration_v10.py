import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        print("Running Migration V10: Setting up gate teams and users...")
        with open("supabase/migration_v10_gate_teams_and_users.sql", "r", encoding="utf-8") as f:
            sql_content = f.read()
            
        # Execute each statement split by semicolon (simple runner)
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
                await conn.commit()
                print(f"Executed: {stmt[:60]}...")
            except Exception as e:
                print(f"Error executing statement: {e}")

if __name__ == "__main__":
    asyncio.run(main())
