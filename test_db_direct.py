import asyncio, asyncpg

async def test():
    try:
        conn = await asyncpg.connect(
            'postgresql://postgres:postgres@127.0.0.1:5434/postgres',
            timeout=5,
            statement_cache_size=0
        )
        result = await conn.fetchval('SELECT 1')
        print(f'DB Connection OK: {result}')
        
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        print(f'Tables found: {len(tables)}')
        for t in tables:
            print(f'  - {t["tablename"]}')
        
        await conn.close()
    except Exception as e:
        print(f'DB ERROR: {e}')

asyncio.run(test())
