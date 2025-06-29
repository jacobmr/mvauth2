import httpx
import json
from typing import List, Dict, Optional
from .config import settings
import os

class SupabaseClient:
    def __init__(self):
        # Extract project ref from DATABASE_URL
        # postgresql://postgres:password@db.wwrzyfekbqwnogkpzfll.supabase.co:5432/postgres
        db_url = settings.database_url
        if "wwrzyfekbqwnogkpzfll" in db_url:
            self.project_ref = "wwrzyfekbqwnogkpzfll"
        else:
            # Extract from URL
            parts = db_url.split("@")
            if len(parts) > 1:
                host_part = parts[1].split(":")[0]
                if "." in host_part:
                    self.project_ref = host_part.split(".")[1]
                else:
                    self.project_ref = "wwrzyfekbqwnogkpzfll"  # fallback
            else:
                self.project_ref = "wwrzyfekbqwnogkpzfll"  # fallback
        
        self.base_url = f"https://{self.project_ref}.supabase.co"
        # Get service key from settings
        self.service_key = settings.supabase_service_key or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind3cnp5ZmVrYnF3bm9na3B6ZmxsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTAzODMyNiwiZXhwIjoyMDY2NjE0MzI2fQ.cqRAnyQl3EOJRtcFAEAEFkHLUBT6KDLStnKBVVdOySY"
        
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    async def get_users(self) -> List[Dict]:
        """Get all active users"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/rest/v1/community_users?is_active=eq.true&select=*",
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Supabase API error: {e}")
                return []
    
    async def create_user(self, user_data: Dict) -> Optional[Dict]:
        """Create a new user"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/rest/v1/community_users",
                    headers=self.headers,
                    json=user_data,
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                return result[0] if result else None
            except Exception as e:
                print(f"Supabase API create error: {e}")
                return None
    
    async def update_user(self, user_id: int, user_data: Dict) -> Optional[Dict]:
        """Update a user"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    f"{self.base_url}/rest/v1/community_users?id=eq.{user_id}",
                    headers=self.headers,
                    json=user_data,
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                return result[0] if result else None
            except Exception as e:
                print(f"Supabase API update error: {e}")
                return None
    
    async def delete_user(self, user_id: int) -> bool:
        """Soft delete a user (set is_active = false)"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    f"{self.base_url}/rest/v1/community_users?id=eq.{user_id}",
                    headers=self.headers,
                    json={"is_active": False},
                    timeout=10.0
                )
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"Supabase API delete error: {e}")
                return False

# Global instance
supabase_client = SupabaseClient()