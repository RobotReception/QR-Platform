import sys
import os
import asyncio

# Resolve project root and append to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    if len(sys.argv) < 2:
        print("❌ Usage: python scratch/make_email_staff.py <user_email>")
        return
        
    email = sys.argv[1].strip()
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    
    async with engine.begin() as conn:
        # 1. Find the user ID from auth.users or profiles by email
        res = await conn.execute(
            text("SELECT id FROM auth.users WHERE email = :email"),
            {"email": email}
        )
        row = res.first()
        if not row:
            print(f"❌ User with email '{email}' not found in the database. Please register first.")
            return
            
        uid = str(row[0])
        
        # 2. Update profiles table
        update_res = await conn.execute(
            text("UPDATE profiles SET is_staff = true WHERE id = :uid"),
            {"uid": uid}
        )
        print(f"✨ Successfully updated profiles table. Rows affected: {update_res.rowcount}")
        print(f"👑 User '{email}' (ID: {uid}) is now an Admin/Staff user!")

if __name__ == '__main__':
    asyncio.run(main())
