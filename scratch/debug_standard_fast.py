import sys
import asyncio
from uuid import UUID

# Force UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

# Set python path
import os
sys.path.insert(0, os.path.abspath("."))

from app.services.fast_generation_service import generate_invitations_fast
from app.database import AsyncSessionLocal

async def test_direct():
    tenant_id = "41006037-931e-4e1f-9a7f-964840982051"
    event_id = "7eeb7810-fdb2-4554-82b1-a7901a2c2e76"
    
    invitations_data = [
        {
            "guest_name": "Debug Guest Standard 1",
            "ticket_class": "normal",
            "guest_count": 1
        }
    ]
    
    async with AsyncSessionLocal() as db:
        try:
            print("Invoking generate_invitations_fast directly...")
            result = await generate_invitations_fast(
                db=db,
                tenant_id=tenant_id,
                event_id=event_id,
                invitations_data=invitations_data,
                layout_config=None,
                generate_pdf=True,
                generate_zip=True,
                upload_individual_barcodes=False
            )
            print("Success! Result:", result)
        except Exception as e:
            print("Error encountered:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct())
