#!/usr/bin/env python3
import asyncio
import asyncpg
from urllib.parse import quote_plus

async def test_connection():
    # Use the exact URL from our .env file
    mvauth_url = "postgresql://postgres:h%40%3FBB5x_uEU3dB%21@db.wwrzyfekbqwnogkpzfll.supabase.co:5432/postgres"
    
    print(f"Testing connection to: postgresql://postgres:***@db.wwrzyfekbqwnogkpzfll.supabase.co:5432/postgres")
    
    try:
        conn = await asyncpg.connect(mvauth_url)
        result = await conn.fetchval("SELECT COUNT(*) FROM community_users")
        print(f"✅ Connected successfully! Found {result} users in community_users table")
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())