import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        print("PLAN_ADDONS IN DATABASE:")
        res = await conn.execute(text("SELECT key, label_ar, step, price_per_unit, is_active FROM plan_addons ORDER BY sort_order"))
        for row in res.mappings():
            status = "ACTIVE" if row['is_active'] else "INACTIVE"
            print(f"- Key: {row['key']:25s} | Step: {row['step']:5d} | Price: {row['price_per_unit']:6.2f} | Status: {status} | Label: {row['label_ar']}")

        print("\nPLANS IN DATABASE:")
        res = await conn.execute(text("SELECT code, name, description, price_monthly FROM plans"))
        for row in res.mappings():
            print(f"- Code: {row['code']}, Name: {row['name']}, Price: {row['price_monthly']}, Desc: {row['description']}")

asyncio.run(main())
