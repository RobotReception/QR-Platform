import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    db_url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5434/postgres"
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        print("Executing ALTER TYPE public.element_type ADD VALUE IF NOT EXISTS 'dynamic_text';")
        # In PostgreSQL, ALTER TYPE ... ADD VALUE cannot run inside a transaction block in some versions,
        # but connection.execution_options(isolation_level="AUTOCOMMIT") can help.
        # Alternatively, we can run it with connection in autocommit mode.
        pass

    # Let's use psycopg2 if we can, or just asyncpg directly with connection autocommit.
    # To run ALTER TYPE ADD VALUE in asyncpg, we must run it outside a transaction.
    # In asyncpg, we can use the raw connection.
    import asyncpg
    conn = await asyncpg.connect("postgresql://postgres:postgres@127.0.0.1:5434/postgres")
    try:
        await conn.execute("ALTER TYPE public.element_type ADD VALUE IF NOT EXISTS 'dynamic_text';")
        print("Enum value added successfully or already exists!")
    except Exception as e:
        print("Error:", e)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
