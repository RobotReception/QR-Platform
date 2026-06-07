import asyncio
import asyncpg
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

async def run():
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='postgres',
        password='postgres',
        database='postgres'
    )
    
    print("--- PLANS FEATURES ---")
    rows = await conn.fetch("SELECT code, name, features FROM public.plans ORDER BY sort_order")
    for r in rows:
        features = r['features']
        if isinstance(features, str):
            features = json.loads(features)
        print(f"{r['name']} ({r['code']}):")
        for f in features:
            print(f"  - {f}")
        
    print("\n--- ALL PLAN LIMITS ---")
    limits = await conn.fetch("""
        SELECT p.code, pl.key, pl.value
        FROM plan_limits pl
        JOIN plans p ON p.id = pl.plan_id
        ORDER BY p.sort_order, pl.key
    """)
    plan_limits = {}
    for l in limits:
        plan_limits.setdefault(l['code'], []).append(f"{l['key']}: {l['value']}")
    
    for plan, lims in plan_limits.items():
        print(f"\nPlan: {plan}")
        for lim in sorted(lims):
            print(f"  - {lim}")

    print("\n--- INACTIVE ADDONS ---")
    addons = await conn.fetch("SELECT key, label_ar, is_active FROM plan_addons WHERE is_active = false")
    for a in addons:
        print(f"{a['key']}: {a['label_ar']} (is_active={a['is_active']})")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
