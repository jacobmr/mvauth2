from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
import os

from utils.database import get_db
from services.jwt_service import JWTService
from repositories.user_repository import UserRepository
from models.user import UserRole

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Application configuration
APPLICATIONS = {
    "arc": {
        "name": "ARC Application System",
        "description": "Architectural Review Committee applications and submissions",
        "url": "https://mvarc.vercel.app",
        "icon": "🏗️",
        "required_permissions": ["access"]
    },
    "qr_gate": {
        "name": "QR Gate Access",
        "description": "Community gate access and management",
        "url": "https://qr.brasilito.org",
        "icon": "🚪",
        "required_permissions": ["access"]
    }
}

async def get_current_user_optional(
    request: Request, 
    token: str = Depends(security), 
    db: AsyncSession = Depends(get_db)
):
    """Get current user from JWT token (optional - returns None if not authenticated)"""
    # Check for token in Authorization header
    if token:
        try:
            payload = JWTService.validate_token(token.credentials)
            user_id = payload["user_id"]
            
            user_repo = UserRepository(db)
            user = await user_repo.get_by_id(user_id)
            
            # If user not found in database but token is valid, create mock user object
            if not user and payload.get("clerk_user_id", "").startswith("test_"):
                # This is a mock user for testing - create user object from token payload
                class MockUser:
                    def __init__(self, payload):
                        self.id = payload["user_id"]
                        self.email = payload["email"]
                        self.full_name = payload["full_name"]
                        self.role = UserRole(payload["role"])
                        self.unit_number = payload.get("unit_number")
                        self.phone_number = payload.get("phone_number")
                        self.is_active = payload.get("is_active", True)
                    
                    def get_permissions_for_service(self, service_name: str):
                        # Super admin has access to everything
                        if self.role == UserRole.SUPER_ADMIN:
                            return ["access", "admin", "manage_users", "view_logs", "super_admin"]
                        
                        # Service-specific permissions for other roles
                        if service_name == "arc":
                            if self.role == UserRole.ARC_ADMIN:
                                return ["access", "admin", "manage_applications", "assign_reviewers", "view_all"]
                            elif self.role == UserRole.ARC_REVIEWER:
                                return ["access", "review", "comment", "approve", "deny"]
                            elif self.role in [UserRole.HOMEOWNER, UserRole.RESIDENT]:
                                return ["access", "submit", "view_own"]
                        elif service_name == "qr_gate":
                            if self.role == UserRole.QR_ADMIN:
                                return ["access", "admin", "manage_gates", "view_logs", "manage_devices"]
                            elif self.role in [UserRole.HOMEOWNER, UserRole.RESIDENT]:
                                return ["access", "resident_access"]
                        
                        return ["access"]
                
                return MockUser(payload)
            
            return user
        except Exception as e:
            print(f"Token validation error: {e}")
            pass
    
    # Check for token in query parameter (for testing)
    query_token = request.query_params.get("token")
    if query_token:
        try:
            payload = JWTService.validate_token(query_token)
            user_id = payload["user_id"]
            
            user_repo = UserRepository(db)
            user = await user_repo.get_by_id(user_id)
            
            # Handle mock users for testing
            if not user and payload.get("clerk_user_id", "").startswith("test_"):
                class MockUser:
                    def __init__(self, payload):
                        self.id = payload["user_id"]
                        self.email = payload["email"]
                        self.full_name = payload["full_name"]
                        self.role = UserRole(payload["role"])
                        self.unit_number = payload.get("unit_number")
                        self.phone_number = payload.get("phone_number")
                        self.is_active = payload.get("is_active", True)
                    
                    def get_permissions_for_service(self, service_name: str):
                        if self.role == UserRole.SUPER_ADMIN:
                            return ["access", "admin", "manage_users", "view_logs", "super_admin"]
                        
                        if service_name == "arc":
                            if self.role == UserRole.ARC_ADMIN:
                                return ["access", "admin", "manage_applications", "assign_reviewers", "view_all"]
                            elif self.role == UserRole.ARC_REVIEWER:
                                return ["access", "review", "comment", "approve", "deny"]
                            elif self.role in [UserRole.HOMEOWNER, UserRole.RESIDENT]:
                                return ["access", "submit", "view_own"]
                        elif service_name == "qr_gate":
                            if self.role == UserRole.QR_ADMIN:
                                return ["access", "admin", "manage_gates", "view_logs", "manage_devices"]
                            elif self.role in [UserRole.HOMEOWNER, UserRole.RESIDENT]:
                                return ["access", "resident_access"]
                        
                        return ["access"]
                
                return MockUser(payload)
            
            return user
        except Exception as e:
            print(f"Token validation error: {e}")
            pass
    
    return None

def get_user_applications(user) -> List[Dict]:
    """Get list of applications user has access to"""
    if not user:
        return []
    
    accessible_apps = []
    
    for app_id, app_config in APPLICATIONS.items():
        # Check if user has required permissions for this app
        permissions = user.get_permissions_for_service(app_id)
        
        # Check if user has any of the required permissions
        has_access = any(perm in permissions for perm in app_config["required_permissions"])
        
        if has_access:
            accessible_apps.append({
                "id": app_id,
                "name": app_config["name"],
                "description": app_config["description"],
                "url": app_config["url"],
                "icon": app_config["icon"],
                "permissions": permissions
            })
    
    return accessible_apps

@router.get("/apps")
async def get_user_apps(
    user = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """API endpoint to get user's accessible applications"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    accessible_apps = get_user_applications(user)
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value
        },
        "applications": accessible_apps,
        "total_access": len(accessible_apps)
    }

@router.get("/user-status")
async def get_user_status(
    user = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """API endpoint to check user authentication status and basic info"""
    if not user:
        return {
            "authenticated": False,
            "user": None,
            "applications": []
        }
    
    accessible_apps = get_user_applications(user)
    
    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value
        },
        "applications": accessible_apps,
        "total_access": len(accessible_apps)
    }

@router.get("/debug-db")
async def debug_database():
    """Debug endpoint to check database configuration"""
    from utils.config import settings
    from utils.database import database_url
    
    # Check environment variables
    env_database_url = os.getenv("DATABASE_URL", "NOT_SET")
    
    return {
        "env_DATABASE_URL": env_database_url[:50] + "..." if len(str(env_database_url)) > 50 else str(env_database_url),
        "settings_database_url": settings.database_url[:50] + "..." if len(settings.database_url) > 50 else settings.database_url,
        "computed_database_url": database_url[:50] + "..." if len(database_url) > 50 else database_url,
        "is_sqlite": database_url.startswith("sqlite"),
        "is_postgresql": database_url.startswith("postgresql"),
        "env_vars_available": {
            "DATABASE_URL": "DATABASE_URL" in os.environ,
            "CLERK_SECRET_KEY": "CLERK_SECRET_KEY" in os.environ,
            "CLERK_PUBLISHABLE_KEY": "CLERK_PUBLISHABLE_KEY" in os.environ,
            "JWT_SECRET_KEY": "JWT_SECRET_KEY" in os.environ
        }
    }

@router.get("/test-login")
async def test_login(email: str = "jacob@reider.us"):
    """Test endpoint to simulate login (REMOVE IN PRODUCTION)"""
    try:
        # Create a mock user for testing without database
        role = UserRole.SUPER_ADMIN if email in ["jacob@brasilito.org", "jacob@reider.us"] else UserRole.HOMEOWNER
        
        mock_user = {
            "id": 1,
            "clerk_user_id": f"test_{email.replace('@', '_')}",
            "email": email,
            "full_name": f"Test User ({email})",
            "unit_number": "101",
            "phone_number": None,
            "role": role.value,
            "is_active": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "last_login": None
        }
        
        # Create token
        access_token = JWTService.create_community_token(mock_user)
        
        return {
            "message": "Test login successful (mock user)",
            "access_token": access_token,
            "user": mock_user,
            "redirect_url": f"https://auth.brasilito.org/?token={access_token}",  # Will be the new community portal
            "instructions": "Use the access_token for API calls or redirect_url for web login"
        }
        
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}