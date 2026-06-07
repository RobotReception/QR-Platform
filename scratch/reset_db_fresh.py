import asyncio
import asyncpg
import sys

sys.stdout.reconfigure(encoding="utf-8")

async def run():
    print("🔄 Connecting to local Supabase Postgres database...")
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='postgres',
        password='postgres',
        database='postgres'
    )
    
    # List of tables to delete
    tables_to_wipe = [
        # 1. Event & Invitation Data
        "public.checkins",
        "public.invitation_deliveries",
        "public.invitations",
        "public.guests",
        "public.event_gates",
        "public.event_gate_users",
        "public.event_registration_forms",
        "public.batch_items",
        "public.generation_batches",
        "public.events",
        
        # 2. Templates & Assets
        "public.template_elements",
        "public.template_assets",
        "public.invite_templates",
        
        # 3. Subscriptions & Usage
        "public.custom_plans",
        "public.subscription_events",
        "public.subscriptions",
        "public.usage_counters",
        
        # 4. Logs
        "public.audit_logs",
        
        # 5. Teams & Memberships
        "public.team_memberships",
        "public.teams",
        "public.memberships",
        "public.invites",
        
        # 6. Tenant & Settings
        "public.tenant_domains",
        "public.tenant_settings",
        "public.tenants",
        
        # 7. Profiles & Auth Users
        "public.profiles",
        "auth.identities",
        "auth.users"
    ]
    
    tx = conn.transaction()
    await tx.start()
    try:
        print("⚠️ Temporarily disabling database constraints and triggers...")
        await conn.execute("SET session_replication_role = 'replica';")
        
        for table in tables_to_wipe:
            print(f"🧹 Clearing table: {table}...")
            await conn.execute(f"DELETE FROM {table};")
            
        print("🔧 Re-enabling database constraints and triggers...")
        await conn.execute("SET session_replication_role = 'origin';")
        
        await tx.commit()
        print("✨ Database reset completed successfully! All users, teams, events, and invitations have been cleared.")
        
    except Exception as e:
        await tx.rollback()
        print(f"❌ Error resetting database: {e}", file=sys.stderr)
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
