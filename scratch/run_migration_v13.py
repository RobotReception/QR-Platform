import asyncio
import asyncpg
import os

async def run():
    migration_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'supabase', 'migration_v13_limits_and_features.sql')

    print(f"Reading migration from {migration_path}...")
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Connect to the DB
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='postgres',
        password='postgres',
        database='postgres'
    )
    
    print("Executing migration_v13_limits_and_features.sql...")
    # asyncpg execute runs SQL in a single transaction if multiple statements are present or as is
    await conn.execute(sql)
    print("Migration v13 executed successfully!")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
