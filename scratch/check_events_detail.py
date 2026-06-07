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
    
    # Check columns of subscriptions table
    columns_rows = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'subscriptions';
    """)
    print("--- COLUMNS IN SUBSCRIPTIONS TABLE ---")
    for r in columns_rows:
        print(f"  {r['column_name']} ({r['data_type']})")

    # Select all rows in events
    events_rows = await conn.fetch("SELECT * FROM events;")
    print(f"\n--- EVENTS ROWS ({len(events_rows)} total) ---")
    for r in events_rows:
        print(dict(r))
        
    await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
