import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='postgres',
        password='postgres',
        database='postgres'
    )
    
    rows = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    
    print("--- TABLES IN PUBLIC SCHEMA ---")
    for r in rows:
        print(r['table_name'])
        
    await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
