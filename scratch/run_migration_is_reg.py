import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def migrate():
    async with AsyncSessionLocal() as db:
        print("Running migration: adding 'is_registration' column to 'invitations' table...")
        await db.execute(text("ALTER TABLE invitations ADD COLUMN IF NOT EXISTS is_registration BOOLEAN DEFAULT FALSE;"))
        await db.commit()
        print("Migration complete!")

if __name__ == '__main__':
    asyncio.run(migrate())
