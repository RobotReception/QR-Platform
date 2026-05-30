import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    db_url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5434/postgres"
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        print("Executing: ALTER TABLE public.template_elements ADD COLUMN IF NOT EXISTS slot_index INTEGER DEFAULT NULL;")
        await conn.execute(text("ALTER TABLE public.template_elements ADD COLUMN IF NOT EXISTS slot_index INTEGER DEFAULT NULL;"))
        await conn.commit()
        
        print("Executing constraint check...")
        try:
            await conn.execute(text("ALTER TABLE public.template_elements ADD CONSTRAINT chk_element_slot_index CHECK (slot_index IS NULL OR slot_index >= 0);"))
            await conn.commit()
            print("Constraint added successfully.")
        except Exception as e:
            print("Constraint might already exist or failed:", e)
            
        print("Migration V8 completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
