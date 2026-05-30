import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    db_url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5434/postgres"
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT enumlabel 
            FROM pg_enum 
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
            WHERE pg_type.typname = 'element_type';
        """))
        print("Enum values for element_type:")
        for row in res:
            print(f"- {row[0]}")

if __name__ == "__main__":
    asyncio.run(main())
