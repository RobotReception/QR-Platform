import asyncio
from sqlalchemy import text
import json
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id, guest_name, metadata FROM invitations"))
        rows = res.mappings().all()
        for r in rows:
            meta = r['metadata'] or {}
            if 'is_registration' in meta or meta.get('is_registration') == True:
                print(f"FOUND Form Registrant: ID={r['id']}, Name={r['guest_name']}, Metadata={json.dumps(meta, ensure_ascii=False)}")
            elif meta.get('imported_from'):
                print(f"FOUND Imported: ID={r['id']}, Name={r['guest_name']}, ImportedFrom={meta.get('imported_from')}")

if __name__ == '__main__':
    asyncio.run(check())
