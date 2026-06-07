import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')
import asyncio
from app.database import get_db
from sqlalchemy import text

async def main():
    async for db in get_db():
        tid = "4327e3d1-40e2-4a4c-af8c-71746bcc7903" # pride idea
        uid = "1f7afb25-8dce-4967-85ed-599caf202060" # محمد جمال الشبلي
        r_perms = await db.execute(text("SELECT * FROM public.get_user_permissions(:tid, :uid)"), {"tid": tid, "uid": uid})
        perms = [row[0] for row in r_perms.fetchall()]
        print(f"Total permissions for محمد جمال الشبلي: {len(perms)}")
        print("Permissions containing 'ui.nav':")
        for p in sorted(perms):
            if "ui.nav" in p:
                print(f"  {p}")
        break

if __name__ == "__main__":
    asyncio.run(main())
