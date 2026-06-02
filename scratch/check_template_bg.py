import io
import asyncio
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database import AsyncSessionLocal
from PIL import Image
import httpx

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            text("SELECT background_url, width_px, height_px, metadata FROM invite_templates WHERE id = 'ae184d33-567c-40e5-a8d4-dfe7aeea5cbd'")
        )
        row = res.mappings().first()
        url = row["background_url"]
        print("Template background URL:", url)
        print("Template canvas width:", row["width_px"], "height:", row["height_px"])
        print("Template metadata:", row["metadata"])
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                img = Image.open(io.BytesIO(resp.content))
                print(f"Downloaded Image format: {img.format} | Size: {img.size} | Mode: {img.mode}")
                img.save("scratch/downloaded_bg_4card.png")
                print("Saved to scratch/downloaded_bg_4card.png")

asyncio.run(main())
