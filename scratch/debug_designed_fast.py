import sys
import asyncio
from unittest.mock import MagicMock
from uuid import UUID
from fastapi import BackgroundTasks

# Force UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

# Set python path
import os
sys.path.insert(0, os.path.abspath("."))

from app.routes.batches import generate_designed_fast, BatchGenerateDesignedFast
from app.auth import CurrentUser
from app.database import AsyncSessionLocal

async def test_direct():
    user_id = UUID("a5c259a6-b701-4bab-9a7a-148d13d2dfd8")
    tenant_id = UUID("41006037-931e-4e1f-9a7f-964840982051")
    event_id = UUID("7eeb7810-fdb2-4554-82b1-a7901a2c2e76")
    template_id = UUID("d606dcca-fb84-423e-b0b1-3df343a1a231")
    
    # Create request body
    body = BatchGenerateDesignedFast(
        event_id=event_id,
        template_id=template_id,
        ticket_class="normal",
        invitations=[
            {
                "guest_name": "Debug Guest 1",
                "guest_count": 1,
                "metadata": {"imported_from": "debug_script"}
            }
        ],
        layout={
            "page_size": "A4",
            "orientation": "portrait",
            "rows": 1,
            "cols": 1,
            "margin_top_mm": 0,
            "margin_bottom_mm": 0,
            "margin_left_mm": 0,
            "margin_right_mm": 0,
            "gap_x_mm": 0,
            "gap_y_mm": 0,
            "barcode_size_px": 420,
            "barcode_size_mode": "contain",
            "show_code_text": False,
            "show_guest_name": False,
            "caption_field": "none",
            "dpi": 300,
            "card_per_page": True,
            "barcode_render": "png",
            "cell_padding_mm": 0
        },
        output_formats=["pdf", "zip"],
        barcode_format="qr"
    )
    
    # Mock Request
    request = MagicMock()
    request.headers = {"X-Tenant-ID": str(tenant_id)}
    
    background_tasks = BackgroundTasks()
    
    # Mock User
    user = CurrentUser(
        id=user_id,
        email="test@example.com",
        role="authenticated"
    )
    
    async with AsyncSessionLocal() as db:
        try:
            print("Invoking generate_designed_fast directly...")
            result = await generate_designed_fast(
                body=body,
                request=request,
                background_tasks=background_tasks,
                user=user,
                db=db
            )
            print("Success! Result:", result)
        except Exception as e:
            print("Error encountered:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct())
