import asyncio
import httpx
from jose import jwt
from app.config import get_settings

async def test_endpoints():
    settings = get_settings()
    
    # User ID: a5c259a6-b701-4bab-9a7a-148d13d2dfd8 (Owner of 41006037-931e-4e1f-9a7f-964840982051)
    user_id = "a5c259a6-b701-4bab-9a7a-148d13d2dfd8"
    tenant_id = "41006037-931e-4e1f-9a7f-964840982051"
    event_id = "7eeb7810-fdb2-4554-82b1-a7901a2c2e76"
    template_id = "d606dcca-fb84-423e-b0b1-3df343a1a231" # normal designed template
    
    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "role": "authenticated",
        "iss": "supabase-demo"
    }
    
    token = jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
        "Content-Type": "application/json"
    }
    
    print("Testing generate-designed-fast API endpoint...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test generate-designed-fast
        payload_fast = {
            "event_id": event_id,
            "template_id": template_id,
            "ticket_class": "normal",
            "invitations": [
                {
                    "guest_name": "Test Guest Fast 1",
                    "guest_count": 1,
                    "metadata": {"imported_from": "test_script"}
                }
            ],
            "layout": {
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
            "output_formats": ["pdf", "zip"],
            "barcode_format": "qr"
        }
        
        try:
            res = await client.post(
                "http://127.0.0.1:8020/api/v1/batches/generate-designed-fast",
                json=payload_fast,
                headers=headers
            )
            print(f"Designed Fast Response Status: {res.status_code}")
            text_safe = res.content.decode('utf-8', errors='replace')
            print(f"Designed Fast Response Body: {text_safe}")
        except Exception as e:
            print(f"Designed Fast request exception: {e}")

        # 2. Test fast-invitations/generate
        print("\nTesting fast-invitations/generate API endpoint...")
        payload_standard = {
            "event_id": event_id,
            "invitations": [
                {
                    "guest_name": "Test Guest Standard 1",
                    "ticket_class": "normal"
                }
            ],
            "generate_pdf": True,
            "generate_zip": True,
            "upload_individual_barcodes": False
        }
        
        try:
            res = await client.post(
                "http://127.0.0.1:8020/api/v1/fast-invitations/generate",
                json=payload_standard,
                headers=headers
            )
            print(f"Standard Fast Response Status: {res.status_code}")
            text_safe = res.content.decode('utf-8', errors='replace')
            print(f"Standard Fast Response Body: {text_safe}")
        except Exception as e:
            print(f"Standard Fast request exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
