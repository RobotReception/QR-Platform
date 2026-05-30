"""Create password_reset_otps table for OTP-based password recovery."""
import asyncio
import asyncpg

DB_URL = "postgresql://postgres:postgres@127.0.0.1:5434/postgres"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS password_reset_otps (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT NOT NULL,
    otp_code TEXT NOT NULL,
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 3,
    is_verified BOOLEAN DEFAULT FALSE,
    reset_token TEXT,
    blocked_until TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_otp_email ON password_reset_otps(email);
CREATE INDEX IF NOT EXISTS idx_otp_reset_token ON password_reset_otps(reset_token);
"""

async def main():
    conn = await asyncpg.connect(DB_URL, statement_cache_size=0)
    try:
        await conn.execute(CREATE_TABLE_SQL)
        print("✅ Table password_reset_otps created successfully!")
        
        # Verify
        result = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'password_reset_otps' ORDER BY ordinal_position"
        )
        print(f"\nColumns ({len(result)}):")
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
