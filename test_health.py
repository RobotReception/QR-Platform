import httpx, asyncio

async def test():
    async with httpx.AsyncClient(timeout=15) as c:
        try:
            r = await c.get("http://127.0.0.1:8020/health")
            print(f"Status: {r.status_code}, Body: {r.text}")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(test())
