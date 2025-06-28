from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from utils.database import get_db
from services.jwt_service import JWTService
from repositories.user_repository import UserRepository
from models.user import UserRole
from models.audit import AuditLog
from utils.config import settings

router = APIRouter()
security = HTTPBearer()

class CommunityInfoResponse(BaseModel):
    name: str
    total_users: int
    active_users: int
    total_residents: int
    total_admins: int
    total_staff: int

class AnnouncementRequest(BaseModel):
    title: str
    message: str
    urgent: bool = False

async def get_current_user(token: str = Depends(security), db: AsyncSession = Depends(get_db)):
    """Get current user from JWT token"""
    try:
        payload = JWTService.validate_token(token.credentials)
        user_id = payload["user_id"]
        
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def require_admin(current_user = Depends(get_current_user)):
    """Require admin role"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:  # Support legacy admin role
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/info", response_model=CommunityInfoResponse)
async def get_community_info(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get community information"""
    user_repo = UserRepository(db)
    
    # Get user counts (including legacy roles during transition)
    all_users = await user_repo.get_all_active_users()
    
    # Homeowners/Residents
    homeowners = await user_repo.get_users_by_role(UserRole.HOMEOWNER)
    legacy_residents = await user_repo.get_users_by_role(UserRole.RESIDENT)
    total_residents = len(homeowners) + len(legacy_residents)
    
    # Admins
    super_admins = await user_repo.get_users_by_role(UserRole.SUPER_ADMIN)
    legacy_admins = await user_repo.get_users_by_role(UserRole.ADMIN)
    total_admins = len(super_admins) + len(legacy_admins)
    
    # Staff (legacy role)
    staff = await user_repo.get_users_by_role(UserRole.STAFF)
    
    return CommunityInfoResponse(
        name=settings.community_name,
        total_users=len(all_users),
        active_users=len(all_users),  # All returned users are active
        total_residents=total_residents,
        total_admins=total_admins,
        total_staff=len(staff)
    )

@router.get("/members")
async def get_active_members(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of active community members (basic info only)"""
    user_repo = UserRepository(db)
    users = await user_repo.get_all_active_users()
    
    # Return basic info only (not full profiles)
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "unit_number": user.unit_number,
            "role": user.role.value
        }
        for user in users
    ]

@router.post("/announcements")
async def send_announcement(
    announcement: AnnouncementRequest,
    request: Request,
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Send community announcement (admin only)"""
    user_repo = UserRepository(db)
    
    # Log the announcement
    await user_repo.log_user_action(
        user_id=admin_user.id,
        service_name="community_auth",
        action="announcement_sent",
        resource="community",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        extra_data=f"Title: {announcement.title}, Urgent: {announcement.urgent}"
    )
    
    # In a real implementation, you'd integrate with email/SMS/push notification services
    # For now, just return success and log the action
    
    return {
        "message": "Announcement logged successfully",
        "title": announcement.title,
        "sent_by": admin_user.full_name,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/activity")
async def get_community_activity(
    days: int = 7,
    limit: int = 50,
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get recent community activity (admin only)"""
    
    # This would require additional database queries to get audit logs
    # For now, return a simple response indicating the feature is available
    
    since_date = datetime.utcnow() - timedelta(days=days)
    
    return {
        "message": "Activity logs available",
        "period": f"Last {days} days",
        "since": since_date.isoformat(),
        "note": "Full audit log implementation would go here"
    }

@router.get("/stats")
async def get_community_stats(
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get community statistics (admin only)"""
    user_repo = UserRepository(db)
    
    # Get basic user stats (including legacy roles during transition)
    all_users = await user_repo.get_all_active_users()
    
    # Homeowners/Residents
    homeowners = await user_repo.get_users_by_role(UserRole.HOMEOWNER)
    legacy_residents = await user_repo.get_users_by_role(UserRole.RESIDENT)
    total_residents = len(homeowners) + len(legacy_residents)
    
    # Admins
    super_admins = await user_repo.get_users_by_role(UserRole.SUPER_ADMIN)
    legacy_admins = await user_repo.get_users_by_role(UserRole.ADMIN)
    total_admins = len(super_admins) + len(legacy_admins)
    
    # Staff (legacy role)
    staff = await user_repo.get_users_by_role(UserRole.STAFF)
    
    # Calculate some basic stats
    recent_logins = len([u for u in all_users if u.last_login and 
                        u.last_login > datetime.utcnow() - timedelta(days=30)])
    
    return {
        "users": {
            "total": len(all_users),
            "residents": total_residents,
            "admins": total_admins,
            "staff": len(staff),
            "recent_logins_30d": recent_logins
        },
        "community": {
            "name": settings.community_name,
        },
        "services": {
            "auth_service": "running",
            "connected_services": ["qr_gate"]  # This could be dynamic based on service registrations
        }
    }