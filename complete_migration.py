import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5434,
    user='postgres',
    password='postgres',
    dbname='postgres',
    sslmode='disable'
)
conn.autocommit = True
cur = conn.cursor()

# Create event_assets table
print("Creating event_assets table...")
cur.execute("""
    CREATE TABLE IF NOT EXISTS public.event_assets (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        event_id UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
        asset_type TEXT NOT NULL,
        file_url TEXT NOT NULL,
        file_name TEXT,
        mime_type TEXT,
        size BIGINT DEFAULT 0,
        metadata JSONB DEFAULT '{}',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
""")

# Create indexes
print("Creating indexes...")
cur.execute("CREATE INDEX IF NOT EXISTS idx_event_assets_event ON public.event_assets(event_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_event_assets_type ON public.event_assets(asset_type)")

# Add capacity column
print("Adding capacity column...")
cur.execute("ALTER TABLE public.events ADD COLUMN IF NOT EXISTS capacity INT")

# Add capacity constraint
print("Adding capacity constraint...")
try:
    cur.execute("ALTER TABLE public.events ADD CONSTRAINT check_capacity_positive CHECK (capacity IS NULL OR capacity > 0)")
except:
    print("Constraint already exists")

# Add token_hash column
print("Adding token_hash column...")
cur.execute("ALTER TABLE public.invitations ADD COLUMN IF NOT EXISTS token_hash TEXT")

# Generate hashes for existing tokens
print("Generating token hashes...")
cur.execute("UPDATE public.invitations SET token_hash = encode(digest(token, 'sha256'), 'hex') WHERE token_hash IS NULL AND token IS NOT NULL")

# Add unique constraint on hash
print("Adding token_hash unique constraint...")
try:
    cur.execute("ALTER TABLE public.invitations ADD CONSTRAINT invitations_token_hash_unique UNIQUE (token_hash)")
except:
    print("Constraint already exists")

print("Migration completed successfully!")
conn.close()
