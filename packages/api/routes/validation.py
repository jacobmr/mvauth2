from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from utils.database import get_db
from services.jwt_service import JWTService
from repositories.user_repository import UserRepository
from utils.config import settings

router = APIRouter()

class TokenValidationRequest(BaseModel):
    token: str
    service_name: str

class TokenValidationResponse(BaseModel):
    valid: bool
    user_id: Optional[int] = None
    clerk_user_id: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    unit_number: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[list] = None
    error: Optional[str] = None

def validate_service_token(service_token: str, expected_service: str) -> bool:
    """Validate service-to-service authentication token"""
    return service_token == settings.service_token

@router.post("/token", response_model=TokenValidationResponse)
async def validate_token_for_service(
    validation_request: TokenValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate JWT token for other community services
    This is called by other services (like QR Gate Service) to validate user tokens
    """
    try:
        # Validate the community JWT token
        payload = JWTService.validate_token(validation_request.token)
        user_id = payload.get("user_id")
        
        if not user_id:
            return TokenValidationResponse(
                valid=False,
                error="Invalid token - no user ID"
            )
        
        # Get user from database to ensure they're still active
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user or not user.is_active:
            return TokenValidationResponse(
                valid=False,
                error="User not found or inactive"
            )
        
        return TokenValidationResponse(
            valid=True,
            user_id=user.id,
            clerk_user_id=user.clerk_user_id,
            email=user.email,
            full_name=user.full_name,
            unit_number=user.unit_number,
            role=user.role.value,
            permissions=user.get_permissions_for_service(validation_request.service_name)
        )
        
    except HTTPException as e:
        return TokenValidationResponse(
            valid=False,
            error=e.detail
        )
    except Exception as e:
        return TokenValidationResponse(
            valid=False,
            error=f"Token validation failed: {str(e)}"
        )

@router.get("/user/{user_id}")
async def get_user_for_service(
    user_id: int,
    service_token: str = Header(..., alias="X-Service-Token"),
    service_name: str = Header(..., alias="X-Service-Name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user data for other services (service-to-service call)
    Requires service token authentication
    """
    # Validate service token
    if not validate_service_token(service_token, service_name):
        raise HTTPException(status_code=403, detail="Invalid service token")
    
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user.id,
            "clerk_user_id": user.clerk_user_id,
            "email": user.email,
            "full_name": user.full_name,
            "unit_number": user.unit_number,
            "phone_number": user.phone_number,
            "role": user.role.value,
            "is_active": user.is_active,
            "permissions": user.get_permissions_for_service(service_name)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

@router.get("/user/by-clerk-id/{clerk_user_id}")
async def get_user_by_clerk_id_for_service(
    clerk_user_id: str,
    service_token: str = Header(..., alias="X-Service-Token"),
    service_name: str = Header(..., alias="X-Service-Name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user data by Clerk ID for other services
    """
    # Validate service token
    if not validate_service_token(service_token, service_name):
        raise HTTPException(status_code=403, detail="Invalid service token")
    
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_clerk_id(clerk_user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user.id,
            "clerk_user_id": user.clerk_user_id,
            "email": user.email,
            "full_name": user.full_name,
            "unit_number": user.unit_number,
            "phone_number": user.phone_number,
            "role": user.role.value,
            "is_active": user.is_active,
            "permissions": user.get_permissions_for_service(service_name)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

@router.post("/permissions")
async def check_user_permissions(
    user_id: int,
    service_name: str,
    required_permissions: list[str],
    service_token: str = Header(..., alias="X-Service-Token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if user has required permissions for a service
    """
    # Validate service token
    if not validate_service_token(service_token, service_name):
        raise HTTPException(status_code=403, detail="Invalid service token")
    
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user or not user.is_active:
            return {"authorized": False, "reason": "User not found or inactive"}
        
        user_permissions = user.get_permissions_for_service(service_name)
        has_permissions = all(perm in user_permissions for perm in required_permissions)
        
        return {
            "authorized": has_permissions,
            "user_permissions": user_permissions,
            "required_permissions": required_permissions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Permission check failed: {str(e)}")