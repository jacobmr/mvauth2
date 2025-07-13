from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List

from utils.database import get_db
from services.jwt_service import JWTService
from repositories.user_repository import UserRepository
from models.user import UserRole

router = APIRouter()
security = HTTPBearer()

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    unit_number: Optional[str] = None
    phone_number: Optional[str] = None

class UserRoleUpdateRequest(BaseModel):
    role: UserRole

class UserResponse(BaseModel):
    id: int
    clerk_user_id: str
    email: str
    full_name: str
    unit_number: Optional[str]
    phone_number: Optional[str]
    role: str
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    last_login: Optional[str]

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

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse(**current_user.to_dict())

@router.get("/by-clerk-id/{clerk_user_id}", response_model=UserResponse)
async def get_user_by_clerk_id(
    clerk_user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user by Clerk ID (for mobile app authentication)"""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_clerk_id(clerk_user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(**user.to_dict())

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdateRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile"""
    user_repo = UserRepository(db)
    
    updated_user = await user_repo.update_by_clerk_id(
        current_user.clerk_user_id,
        full_name=update_data.full_name,
        unit_number=update_data.unit_number,
        phone_number=update_data.phone_number
    )
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(**updated_user.to_dict())

@router.get("/community", response_model=List[UserResponse])
async def get_community_members(
    active_only: bool = True,
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get list of community members (admin only)"""
    user_repo = UserRepository(db)
    
    if active_only:
        users = await user_repo.get_all_active_users()
    else:
        # For now, just return active users - could add get_all_users method
        users = await user_repo.get_all_active_users()
    
    return [UserResponse(**user.to_dict()) for user in users]

@router.get("/community/residents", response_model=List[UserResponse])
async def get_residents(
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get list of homeowners (admin only)"""
    user_repo = UserRepository(db)
    homeowners = await user_repo.get_users_by_role(UserRole.HOMEOWNER)
    # Also include legacy residents during transition
    legacy_residents = await user_repo.get_users_by_role(UserRole.RESIDENT)
    all_residents = homeowners + legacy_residents
    return [UserResponse(**user.to_dict()) for user in all_residents]

@router.get("/community/admins", response_model=List[UserResponse])
async def get_admins(
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get list of admins (admin only)"""
    user_repo = UserRepository(db)
    super_admins = await user_repo.get_users_by_role(UserRole.SUPER_ADMIN)
    # Also include legacy admins during transition
    legacy_admins = await user_repo.get_users_by_role(UserRole.ADMIN)
    all_admins = super_admins + legacy_admins
    return [UserResponse(**user.to_dict()) for user in all_admins]

@router.post("/{user_id}/role")
async def assign_user_role(
    user_id: int,
    role_update: UserRoleUpdateRequest,
    request: Request,
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Assign role to user (admin only)"""
    user_repo = UserRepository(db)
    
    # Get the target user
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update the role
    updated_user = await user_repo.update_by_clerk_id(
        target_user.clerk_user_id,
        role=role_update.role
    )
    
    # Log the role change
    await user_repo.log_user_action(
        user_id=admin_user.id,
        service_name="community_auth",
        action="role_changed",
        resource=f"user:{user_id}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        extra_data=f"Changed role from {target_user.role.value} to {role_update.role.value}"
    )
    
    return {"message": "Role updated successfully", "user": updated_user.to_dict()}

@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    request: Request,
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate user (admin only)"""
    user_repo = UserRepository(db)
    
    # Get the target user
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deactivation
    if target_user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    
    # Deactivate user
    updated_user = await user_repo.deactivate_user(target_user.clerk_user_id)
    
    # Log the deactivation
    await user_repo.log_user_action(
        user_id=admin_user.id,
        service_name="community_auth",
        action="user_deactivated",
        resource=f"user:{user_id}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        extra_data=f"Deactivated user: {target_user.email}"
    )
    
    return {"message": "User deactivated successfully", "user": updated_user.to_dict()}

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: int,
    request: Request,
    admin_user = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Activate user (admin only)"""
    user_repo = UserRepository(db)
    
    # Get the target user
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Activate user
    updated_user = await user_repo.update_by_clerk_id(
        target_user.clerk_user_id,
        is_active=True
    )
    
    # Log the activation
    await user_repo.log_user_action(
        user_id=admin_user.id,
        service_name="community_auth",
        action="user_activated",
        resource=f"user:{user_id}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        extra_data=f"Activated user: {target_user.email}"
    )
    
    return {"message": "User activated successfully", "user": updated_user.to_dict()}