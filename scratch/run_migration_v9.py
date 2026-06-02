import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        print("Running Migration V9: Adding guest_count column to invitations...")
        try:
            await conn.execute(text("ALTER TABLE public.invitations ADD COLUMN IF NOT EXISTS guest_count INT NOT NULL DEFAULT 1;"))
            await conn.commit()
            print("Successfully added guest_count column.")
        except Exception as e:
            print("Error adding guest_count column:", e)
            
        print("Running Migration V9: Updating public.validate_checkin function...")
        # Read the function DDL from the migration sql file
        with open("supabase/migration_v9_guest_count_scans.sql", "r", encoding="utf-8") as f:
            sql_content = f.read()
            
        # The validate_checkin starts with CREATE OR REPLACE FUNCTION
        start_idx = sql_content.find("CREATE OR REPLACE FUNCTION")
        if start_idx != -1:
            function_sql = sql_content[start_idx:]
            try:
                await conn.execute(text(function_sql))
                await conn.commit()
                print("Successfully updated validate_checkin function.")
            except Exception as e:
                print("Error updating validate_checkin function:", e)
        else:
            print("Could not find function definition in migration file!")

if __name__ == "__main__":
    asyncio.run(main())
