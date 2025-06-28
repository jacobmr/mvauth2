from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum

from utils.database import get_db
from services.jwt_service import JWTService
from repositories.user_repository import UserRepository
from models.user import UserRole

router = APIRouter()
security = HTTPBearer()

class RoleAssignmentRequest(BaseModel):
    user_id: int
    role: UserRole
    reason: Optional[str] = None

class BulkRoleAssignmentRequest(BaseModel):
    assignments: List[RoleAssignmentRequest]

class ApplicationRoles(BaseModel):
    application: str
    roles: List[str]
    description: str

class UserRoleInfo(BaseModel):
    id: int
    email: str
    full_name: str
    current_role: str
    unit_number: Optional[str]
    permissions: Dict[str, List[str]]  # service_name -> permissions
    last_login: Optional[str]
    is_active: bool

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

async def require_super_admin(current_user = Depends(get_current_user)):
    """Require super admin role for role management"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:  # Support legacy admin
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user

@router.get("/available-roles", response_model=List[ApplicationRoles])
async def get_available_roles(
    super_admin = Depends(require_super_admin)
):
    """Get all available roles organized by application"""
    return [
        ApplicationRoles(
            application="community",
            roles=["super_admin", "homeowner", "guest"],
            description="Community-wide roles for general access"
        ),
        ApplicationRoles(
            application="arc",
            roles=["arc_admin", "arc_reviewer", "homeowner"],
            description="ARC application system for architectural review"
        ),
        ApplicationRoles(
            application="qr_gate", 
            roles=["qr_admin", "qr_scanner", "homeowner"],
            description="QR Gate system for community access control"
        )
    ]

@router.get("/users", response_model=List[UserRoleInfo])
async def get_all_users_with_roles(
    super_admin = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all users with their current roles and permissions"""
    user_repo = UserRepository(db)
    users = await user_repo.get_all_active_users()
    
    result = []
    for user in users:
        # Get permissions for all services
        permissions = {
            "community": user.get_permissions_for_service("community_auth"),
            "arc": user.get_permissions_for_service("arc"),
            "qr_gate": user.get_permissions_for_service("qr_gate")
        }
        
        result.append(UserRoleInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            current_role=user.role.value,
            unit_number=user.unit_number,
            permissions=permissions,
            last_login=user.last_login.isoformat() if user.last_login else None,
            is_active=user.is_active
        ))
    
    return result

@router.post("/assign")
async def assign_user_role(
    assignment: RoleAssignmentRequest,
    request: Request,
    super_admin = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Assign a role to a user"""
    user_repo = UserRepository(db)
    
    # Get the target user
    target_user = await user_repo.get_by_id(assignment.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Store old role for logging
    old_role = target_user.role.value
    
    # Update the user's role
    updated_user = await user_repo.update_by_clerk_id(
        target_user.clerk_user_id,
        role=assignment.role
    )
    
    # Log the role change
    reason_text = f" (Reason: {assignment.reason})" if assignment.reason else ""
    await user_repo.log_user_action(
        user_id=super_admin.id,
        service_name="community_auth",
        action="role_assigned",
        resource=f"user:{assignment.user_id}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        extra_data=f"Changed role from {old_role} to {assignment.role.value}{reason_text}"
    )
    
    return {
        "success": True,
        "message": f"Role updated from {old_role} to {assignment.role.value}",
        "user": {
            "id": updated_user.id,
            "email": updated_user.email,
            "full_name": updated_user.full_name,
            "new_role": updated_user.role.value
        }
    }

@router.post("/assign-bulk")
async def assign_bulk_roles(
    bulk_assignment: BulkRoleAssignmentRequest,
    request: Request,
    super_admin = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Assign roles to multiple users at once"""
    user_repo = UserRepository(db)
    results = []
    errors = []
    
    for assignment in bulk_assignment.assignments:
        try:
            # Get the target user
            target_user = await user_repo.get_by_id(assignment.user_id)
            if not target_user:
                errors.append(f"User {assignment.user_id} not found")
                continue
            
            # Store old role for logging
            old_role = target_user.role.value
            
            # Update the user's role
            updated_user = await user_repo.update_by_clerk_id(
                target_user.clerk_user_id,
                role=assignment.role
            )
            
            # Log the role change
            reason_text = f" (Reason: {assignment.reason})" if assignment.reason else ""
            await user_repo.log_user_action(
                user_id=super_admin.id,
                service_name="community_auth",
                action="bulk_role_assigned",
                resource=f"user:{assignment.user_id}",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                extra_data=f"Bulk update: {old_role} → {assignment.role.value}{reason_text}"
            )
            
            results.append({
                "user_id": assignment.user_id,
                "email": updated_user.email,
                "old_role": old_role,
                "new_role": assignment.role.value,
                "success": True
            })
            
        except Exception as e:
            errors.append(f"Failed to update user {assignment.user_id}: {str(e)}")
    
    return {
        "total_processed": len(bulk_assignment.assignments),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }

@router.get("/user/{user_id}/permissions")
async def get_user_permissions(
    user_id: int,
    super_admin = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed permissions for a specific user across all services"""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value
        },
        "permissions": {
            "community_auth": user.get_permissions_for_service("community_auth"),
            "arc": user.get_permissions_for_service("arc"),
            "qr_gate": user.get_permissions_for_service("qr_gate"),
            "default": user.get_permissions_for_service("unknown_service")
        }
    }

@router.get("/role-statistics")
async def get_role_statistics(
    super_admin = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about role distribution in the community"""
    user_repo = UserRepository(db)
    
    # Count users by role
    role_counts = {}
    for role in UserRole:
        users = await user_repo.get_users_by_role(role)
        if users:  # Only include roles that have users
            role_counts[role.value] = len(users)
    
    # Get total active users
    all_users = await user_repo.get_all_active_users()
    
    return {
        "total_active_users": len(all_users),
        "role_distribution": role_counts,
        "applications": {
            "arc": {
                "admins": role_counts.get("arc_admin", 0),
                "reviewers": role_counts.get("arc_reviewer", 0),
                "total_access": (
                    role_counts.get("arc_admin", 0) + 
                    role_counts.get("arc_reviewer", 0) + 
                    role_counts.get("homeowner", 0) +
                    role_counts.get("resident", 0)  # Legacy
                )
            },
            "qr_gate": {
                "admins": role_counts.get("qr_admin", 0),
                "scanners": role_counts.get("qr_scanner", 0),
                "total_access": (
                    role_counts.get("qr_admin", 0) + 
                    role_counts.get("qr_scanner", 0) + 
                    role_counts.get("homeowner", 0) +
                    role_counts.get("resident", 0)  # Legacy
                )
            }
        }
    }