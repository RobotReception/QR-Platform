import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://postgres:postgres@127.0.0.1:5434/postgres', statement_cache_size=0)
    result = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'password_reset_otps' ORDER BY ordinal_position"
    )
    print(f"Columns ({len(result)}):")
    for row in result:
        print(f"  - {row['column_name']}: {row['data_type']}")
    await conn.close()

asyncio.run(main())
