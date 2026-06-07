import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, name, code, description FROM plans"))
        plans = res.all()
        print("--- PLANS ---")
        for plan in plans:
            print(f"ID: {plan[0]} | Name: {plan[1]} | Code: {plan[2]} | Desc: {plan[3]}")
            
        res_limits = await conn.execute(text("SELECT plan_id, key, value, period FROM plan_limits"))
        limits = res_limits.all()
        print("\n--- PLAN LIMITS ---")
        for limit in limits:
            print(f"Plan ID: {limit[0]} | Key: {limit[1]} | Value: {limit[2]} | Period: {limit[3]}")

asyncio.run(main())
