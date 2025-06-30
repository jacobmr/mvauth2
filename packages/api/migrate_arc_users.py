#!/usr/bin/env python3
"""
Migration script to transfer users from ARC app to centralized MVAuth2 system.

This script:
1. Connects to the ARC Supabase database (Prisma schema)
2. Extracts users from the 'users' table
3. Maps ARC user data to MVAuth2 schema
4. Inserts users into the centralized auth 'community_users' table
5. Creates app-specific roles for ARC app
"""

import asyncio
import asyncpg
import os
from datetime import datetime
from typing import List, Dict, Any
import sys
from urllib.parse import quote_plus

# Database URLs
PASSWORD = "h@?BB5x_uEU3dB!"
ENCODED_PASSWORD = quote_plus(PASSWORD)

# ARC app uses a different Supabase project
ARC_DATABASE_URL = f"postgresql://postgres.tbtpzvmyamrckfvhmiju:{ENCODED_PASSWORD}@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# MVAuth2 uses the current Supabase project
MVAUTH_DATABASE_URL = f"postgresql://postgres:{ENCODED_PASSWORD}@db.wwrzyfekbqwnogkpzfll.supabase.co:5432/postgres"

# Role mapping from ARC to MVAuth2
ARC_TO_MVAUTH_ROLES = {
    "admin": "ADMIN",
    "reviewer": "ADMIN", 
    "submitter": "USER",
    "builder": "USER",
    "architect": "USER"
}

# ARC app-specific role mapping
ARC_APP_ROLES = {
    "admin": "admin",
    "reviewer": "reviewer", 
    "submitter": "owner",
    "builder": "owner",
    "architect": "owner"
}

async def connect_to_database(database_url: str):
    """Connect to PostgreSQL database"""
    try:
        conn = await asyncpg.connect(database_url)
        print(f"✅ Connected to database")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

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

async def check_existing_user(conn, email: str) -> bool:
    """Check if user already exists in MVAuth2 system"""
    try:
        query = "SELECT id FROM community_users WHERE email = $1"
        result = await conn.fetchval(query, email)
        return result is not None
    except Exception as e:
        print(f"❌ Error checking existing user {email}: {e}")
        return False

async def insert_mvauth_user(conn, user_data: Dict[str, Any]) -> int:
    """Insert user into MVAuth2 community_users table"""
    try:
        query = """
        INSERT INTO community_users 
        (clerk_user_id, email, full_name, role, unit_number, phone_number, is_active, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
        """
        
        user_id = await conn.fetchval(
            query,
            "",  # clerk_user_id - will be filled when they first login
            user_data["email"],
            user_data["full_name"],
            user_data["role"],
            user_data.get("unit_number"),
            user_data.get("phone_number"),
            True,  # is_active
            user_data["created_at"],
            user_data["updated_at"]
        )
        return user_id
    except Exception as e:
        print(f"❌ Failed to insert user {user_data['email']}: {e}")
        return None

async def insert_arc_app_role(conn, user_id: int, arc_role: str) -> bool:
    """Insert ARC app-specific role for user"""
    try:
        app_role = ARC_APP_ROLES.get(arc_role, "owner")
        
        query = """
        INSERT INTO user_app_roles (user_id, app_name, role, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id, app_name) DO UPDATE SET
        role = EXCLUDED.role,
        updated_at = EXCLUDED.updated_at
        """
        
        await conn.execute(
            query,
            user_id,
            "arc",
            app_role,
            datetime.now(),
            datetime.now()
        )
        return True
    except Exception as e:
        print(f"❌ Failed to insert ARC app role for user {user_id}: {e}")
        return False

async def migrate_users():
    """Main migration function"""
    print("🚀 Starting ARC to MVAuth2 user migration...")
    
    # Connect to ARC database
    print("🔗 Connecting to ARC database...")
    arc_conn = await connect_to_database(ARC_DATABASE_URL)
    
    # Connect to MVAuth2 database  
    print("🔗 Connecting to MVAuth2 database...")
    mvauth_conn = await connect_to_database(MVAUTH_DATABASE_URL)
    
    try:
        # Fetch ARC users
        arc_users = await fetch_arc_users(arc_conn)
        
        if not arc_users:
            print("⚠️ No users found in ARC database")
            return
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for arc_user in arc_users:
            email = arc_user["email"]
            print(f"\n👤 Processing user: {email}")
            
            # Check if user already exists in MVAuth2
            if await check_existing_user(mvauth_conn, email):
                print(f"⏭️ User {email} already exists in MVAuth2, skipping...")
                skipped_count += 1
                continue
            
            # Map ARC user data to MVAuth2 schema
            mvauth_role = ARC_TO_MVAUTH_ROLES.get(arc_user["role"], "USER")
            
            user_data = {
                "email": email,
                "full_name": arc_user["name"] or email,
                "role": mvauth_role,
                "unit_number": None,  # ARC doesn't have unit numbers
                "phone_number": arc_user["phone"],
                "created_at": arc_user["created_at"],
                "updated_at": arc_user["updated_at"]
            }
            
            # Insert user into MVAuth2
            mvauth_user_id = await insert_mvauth_user(mvauth_conn, user_data)
            
            if mvauth_user_id:
                print(f"✅ Created MVAuth2 user ID: {mvauth_user_id}")
                
                # Add ARC app-specific role
                if await insert_arc_app_role(mvauth_conn, mvauth_user_id, arc_user["role"]):
                    print(f"✅ Added ARC app role: {ARC_APP_ROLES.get(arc_user['role'], 'owner')}")
                    migrated_count += 1
                else:
                    print(f"⚠️ Failed to add ARC app role")
                    error_count += 1
            else:
                print(f"❌ Failed to create MVAuth2 user")
                error_count += 1
        
        # Summary
        print(f"\n📈 Migration Summary:")
        print(f"✅ Successfully migrated: {migrated_count} users")
        print(f"⏭️ Skipped (already exist): {skipped_count} users")
        print(f"❌ Errors: {error_count} users")
        print(f"📊 Total processed: {len(arc_users)} users")
        
    finally:
        await arc_conn.close()
        await mvauth_conn.close()
        print("🔐 Database connections closed")

if __name__ == "__main__":
    print("🏗️ ARC to MVAuth2 User Migration Script")
    print("=" * 50)
    
    # Run the migration
    asyncio.run(migrate_users())
    
    print("\n🎉 Migration completed!")
    print("\nNext steps:")
    print("1. Test the user management interface at https://web.brasilito.org/admin")
    print("2. Verify users can login with Clerk authentication") 
    print("3. Update ARC app to use centralized auth endpoints")