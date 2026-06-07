import asyncio
from sqlalchemy import text
from app.database import get_db

async def main():
    async for db in get_db():
        for t in ['event_gates', 'teams', 'team_memberships']:
            print(f"=== {t} ===")
            col_res = await db.execute(text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{t}' AND table_schema = 'public';
            """))
            for col in col_res.all():
                print(f"  * {col[0]} ({col[1]}, nullable={col[2]})")
            print()
        break

if __name__ == '__main__':
    asyncio.run(main())
