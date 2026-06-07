import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        try:
            # Query the users table in the database
            res = await conn.execute(text("SELECT id, email, full_name, is_staff, is_active FROM users"))
            users = res.fetchall()
            print("Registered Users:")
            for u in users:
                print(f"ID: {u[0]} | Email: {u[1]} | Name: {u[2]} | Staff: {u[3]} | Active: {u[4]}")
        except Exception as e:
            print("DB ERROR:", e)

asyncio.run(main())
