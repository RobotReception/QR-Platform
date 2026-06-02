import io
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings
from PIL import Image

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT background_url FROM invite_templates WHERE id = 'd606dcca-fb84-423e-b0b1-3df343a1a231'")
        )
        row = res.mappings().first()
        url = row["background_url"]
        
        # Download background
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                img = Image.open(io.BytesIO(resp.content))
                print(f"Image format: {img.format} | Size: {img.size} | Mode: {img.mode}")
                # Save it locally for checking
                img.save("scratch/downloaded_bg.png")
                print("Saved background to scratch/downloaded_bg.png")

asyncio.run(main())
