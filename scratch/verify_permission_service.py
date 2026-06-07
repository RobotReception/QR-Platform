import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')
import asyncio
from app.database import get_db
from app.services.permission_service import has_permission

async def main():
    async for db in get_db():
        tid = "4327e3d1-40e2-4a4c-af8c-71746bcc7903" # pride idea
        uid = "1f7afb25-8dce-4967-85ed-599caf202060" # محمد جمال الشبلي (member)
        
        print("Testing backend has_permission for Member:")
        
        # Test ui.nav.users (should be False)
        ok1 = await has_permission(db, tid, uid, "ui.nav.users")
        print(f"  has_permission('ui.nav.users'): {ok1}")
        
        # Test ui.nav.events (should be True)
        ok2 = await has_permission(db, tid, uid, "ui.nav.events")
        print(f"  has_permission('ui.nav.events'): {ok2}")
        
        # Test legacy members.view (should be False)
        ok3 = await has_permission(db, tid, uid, "members.view")
        print(f"  has_permission('members.view'): {ok3}")
        
        # Test legacy events.view (should be True)
        ok4 = await has_permission(db, tid, uid, "events.view")
        print(f"  has_permission('events.view'): {ok4}")
        
        # Test assert expectations
        assert not ok1, "ui.nav.users should be False"
        assert ok2, "ui.nav.events should be True"
        assert not ok3, "members.view should be False"
        assert ok4, "events.view should be True"
        
        print("\nAll backend permission assertions passed successfully!")
        break

if __name__ == "__main__":
    asyncio.run(main())
