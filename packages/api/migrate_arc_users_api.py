#!/usr/bin/env python3
"""
Migration script to transfer users from ARC app to centralized MVAuth2 system using REST API.

This script:
1. Connects to the ARC Supabase database (Prisma schema)
2. Extracts users from the 'users' table
3. Maps ARC user data to MVAuth2 schema
4. Uses MVAuth2 REST API to create users (same as the admin interface)
"""

import asyncio
import asyncpg
import httpx
import json
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import quote_plus

# Database and API URLs
PASSWORD = "h@?BB5x_uEU3dB!"
ENCODED_PASSWORD = quote_plus(PASSWORD)

# ARC database
ARC_DATABASE_URL = f"postgresql://postgres.tbtpzvmyamrckfvhmiju:{ENCODED_PASSWORD}@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# MVAuth2 API
MVAUTH_API_URL = "https://auth.brasilito.org"
ADMIN_EMAIL = "jacob@reider.us"

# Role mapping from ARC to MVAuth2
ARC_TO_MVAUTH_ROLES = {
    "admin": "ADMIN",
    "reviewer": "ADMIN", 
    "submitter": "USER",
    "builder": "USER",
    "architect": "USER"
}

async def connect_to_arc_database():
    """Connect to ARC PostgreSQL database"""
    try:
        conn = await asyncpg.connect(ARC_DATABASE_URL)
        print(f"✅ Connected to ARC database")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to ARC database: {e}")
        return None

async def fetch_arc_users(conn):
    """Fetch all users from ARC database"""
    try:
        query = """
        SELECT id, email, name, role, organization, phone, created_at, updated_at
        FROM users 
        WHERE email IS NOT NULL
        ORDER BY created_at ASC
        """
        rows = await conn.fetch(query)
        print(f"📊 Found {len(rows)} users in ARC database")
        return rows
    except Exception as e:
        print(f"❌ Failed to fetch ARC users: {e}")
        return []

async def check_user_exists(client: httpx.AsyncClient, email: str) -> bool:
    """Check if user already exists using MVAuth2 API"""
    try:
        response = await client.get(
            f"{MVAUTH_API_URL}/admin/api/users",
            headers={"X-User-Email": ADMIN_EMAIL}
        )
        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])
            return any(user.get("email") == email for user in users)
        return False
    except Exception as e:
        print(f"❌ Error checking if user {email} exists: {e}")
        return False

async def create_mvauth_user(client: httpx.AsyncClient, user_data: Dict[str, Any]) -> bool:
    """Create user using MVAuth2 API"""
    try:
        response = await client.post(
            f"{MVAUTH_API_URL}/admin/api/users",
            headers={
                "X-User-Email": ADMIN_EMAIL,
                "Content-Type": "application/json"
            },
            json=user_data
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ Created user: {user_data['email']}")
                return True
            else:
                print(f"❌ API error creating user {user_data['email']}: {result.get('error', 'Unknown error')}")
                print(f"   Full response: {result}")
                return False
        else:
            print(f"❌ HTTP error creating user {user_data['email']}: {response.status_code}")
            print(f"   Response text: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Failed to create user {user_data['email']}: {e}")
        return False

async def migrate_users():
    """Main migration function"""
    print("🚀 Starting ARC to MVAuth2 user migration (via REST API)...")
    
    # Connect to ARC database
    arc_conn = await connect_to_arc_database()
    if not arc_conn:
        return
    
    # Create HTTP client for API calls
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Fetch ARC users
            arc_users = await fetch_arc_users(arc_conn)
            
            if not arc_users:
                print("⚠️ No users found in ARC database")
                return
            
            migrated_count = 0
            skipped_count = 0
            error_count = 0
            
            # Process all users
            
            for arc_user in arc_users:
                email = arc_user["email"]
                print(f"\n👤 Processing user: {email}")
                
                # Skip jacob@reider.us since we know it exists
                if email == "jacob@reider.us":
                    print(f"⏭️ Skipping {email} (already exists)")
                    skipped_count += 1
                    continue
                
                # Check if user already exists
                if await check_user_exists(client, email):
                    print(f"⏭️ User {email} already exists in MVAuth2, skipping...")
                    skipped_count += 1
                    continue
                
                # Map ARC user data to MVAuth2 schema
                mvauth_role = ARC_TO_MVAUTH_ROLES.get(arc_user["role"], "USER")
                
                user_data = {
                    "email": email,
                    "full_name": arc_user["name"] or email,
                    "role": mvauth_role,
                    "status": "active",
                    "phone_number": arc_user["phone"],
                    "unit_number": ""  # ARC doesn't have unit numbers
                }
                
                print(f"   Sending user data: {user_data}")
                
                # Create user via API
                if await create_mvauth_user(client, user_data):
                    migrated_count += 1
                    print(f"✅ Migrated {email} with role {mvauth_role}")
                else:
                    error_count += 1
            
            # Summary
            print(f"\n📈 Migration Summary:")
            print(f"✅ Successfully migrated: {migrated_count} users")
            print(f"⏭️ Skipped (already exist): {skipped_count} users")
            print(f"❌ Errors: {error_count} users")
            print(f"📊 Total processed: {len(arc_users)} users")
            
        finally:
            await arc_conn.close()
            print("🔐 ARC database connection closed")

if __name__ == "__main__":
    print("🏗️ ARC to MVAuth2 User Migration Script (REST API)")
    print("=" * 55)
    
    # Run the migration
    asyncio.run(migrate_users())
    
    print("\n🎉 Migration completed!")
    print("\nNext steps:")
    print("1. Check the user management interface at https://web.brasilito.org/admin")
    print("2. Verify migrated users appear in the user list") 
    print("3. Test that users can login with Clerk authentication")
    print("4. Update ARC app to use centralized auth endpoints")