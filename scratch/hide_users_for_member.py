import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')
import asyncio
from app.database import get_db
from sqlalchemy import text

async def main():
    async for db in get_db():
        role_id = "9d57b9bf-deba-4b76-85ff-b412ac05124f" # Member in pride idea
        
        # Delete ui.nav.users and members.view from this role
        await db.execute(text("""
            DELETE FROM role_permissions
            WHERE role_id = :rid AND permission_key IN ('ui.nav.users', 'members.view')
        """), {"rid": role_id})
        
        await db.commit()
        print("Successfully removed ui.nav.users and members.view from Member role in pride idea!")
        break

if __name__ == "__main__":
    asyncio.run(main())
