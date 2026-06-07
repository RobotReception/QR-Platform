import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def fix():
    async with AsyncSessionLocal() as db:
        print("Fixing existing database records...")
        res = await db.execute(text("""
            UPDATE invitations
            SET is_registration = true
            WHERE (metadata->>'is_registration')::boolean = true;
        """))
        await db.commit()
        print(f"Updated {res.rowcount} row(s) to is_registration=true")

if __name__ == '__main__':
    asyncio.run(fix())
