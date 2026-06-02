import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    db = AsyncSessionLocal()
    try:
        # Get table definition/columns/defaults
        col_res = await db.execute(text("""
            SELECT column_name, column_default, data_type
            FROM information_schema.columns
            WHERE table_name = 'invitations'
        """))
        print("COLUMNS:")
        for r in col_res.mappings().all():
            print(f"{r['column_name']}: default={r['column_default']}, type={r['data_type']}")
        
        # Get triggers
        trig_res = await db.execute(text("""
            SELECT trigger_name, event_manipulation, action_statement
            FROM information_schema.triggers
            WHERE event_object_table = 'invitations'
        """))
        print("\nTRIGGERS:")
        for r in trig_res.mappings().all():
            print(f"{r['trigger_name']} during {r['event_manipulation']}: {r['action_statement']}")
    finally:
        await db.close()

if __name__ == "__main__":
    import os
    os.environ["PYTHONIOENCODING"] = "utf-8"
    asyncio.run(check())
