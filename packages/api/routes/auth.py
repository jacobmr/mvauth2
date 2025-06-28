from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from utils.database import get_db
from services.clerk_service import clerk_service
from services.jwt_service import JWTService
from repositories.user_repository import UserRepository
from models.user import UserRole

router = APIRouter()
security = HTTPBearer()

class LoginRequest(BaseModel):
    service: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    expires_in: int

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/login", response_model=LoginResponse)
async def login_with_clerk(
    request: Request,
    login_data: LoginRequest,
    token: str = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange Clerk JWT for Community Access Token
    """
    try:
        # Extract Clerk token (remove 'Bearer ' prefix)
        clerk_token = token.credentials
        
        # Verify Clerk token and get user info
        clerk_user_data = await clerk_service.verify_clerk_token(clerk_token)
        
        # Get or create user in our database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_clerk_id(clerk_user_data["clerk_user_id"])
        
        if not user:
            # Create new user from Clerk data
            # Determine if user should be super admin based on email
            from utils.config import settings
            role = UserRole.SUPER_ADMIN if clerk_user_data["email"] in settings.admin_emails else UserRole.HOMEOWNER
            
            user = await user_repo.create(
                clerk_user_id=clerk_user_data["clerk_user_id"],
                email=clerk_user_data["email"],
                full_name=clerk_user_data["full_name"],
                phone_number=clerk_user_data.get("phone_number"),
                role=role
            )
        else:
            # Update existing user with latest Clerk data
            user = await user_repo.update_by_clerk_id(
                clerk_user_data["clerk_user_id"],
                email=clerk_user_data["email"],
                full_name=clerk_user_data["full_name"],
                phone_number=clerk_user_data.get("phone_number")
            )
        
        # Update last login
        await user_repo.update_last_login(clerk_user_data["clerk_user_id"])
        
        # Create community tokens
        user_dict = user.to_dict()
        access_token = JWTService.create_community_token(user_dict)
        refresh_token = JWTService.create_refresh_token(user.id)
        
        # Log the login
        await user_repo.log_user_action(
            user_id=user.id,
            service_name=login_data.service or "community_auth",
            action="login",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_dict,
            expires_in=60 * 24 * 7 * 60  # 7 days in seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/refresh")
async def refresh_token(
    refresh_data: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        # Validate refresh token
        payload = JWTService.validate_refresh_token(refresh_data.refresh_token)
        user_id = payload["user_id"]
        
        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        # Create new access token
        user_dict = user.to_dict()
        new_access_token = JWTService.create_community_token(user_dict)
        new_refresh_token = JWTService.create_refresh_token(user.id)
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": user_dict,
            "expires_in": 60 * 24 * 7 * 60  # 7 days in seconds
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")

@router.post("/logout")
async def logout(
    request: Request,
    token: str = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user (mainly for logging purposes)
    """
    try:
        # Validate token
        payload = JWTService.validate_token(token.credentials)
        user_id = payload["user_id"]
        
        # Log the logout
        user_repo = UserRepository(db)
        await user_repo.log_user_action(
            user_id=user_id,
            service_name="community_auth",
            action="logout",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        # Even if token is invalid, return success for logout
        return {"message": "Logged out successfully"}

@router.get("/profile")
async def get_profile(
    token: str = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile
    """
    try:
        # Validate token
        payload = JWTService.validate_token(token.credentials)
        user_id = payload["user_id"]
        
        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")

@router.get("/login")
async def initiate_sso_login(provider: str = "google", redirect_url: Optional[str] = None):
    """
    Initiate SSO login with specified provider (Google, Apple, etc.)
    """
    try:
        # For now, redirect to Clerk's hosted sign-in page
        # In production, this would integrate with Clerk's frontend JS SDK
        from utils.config import settings
        
        # Construct Clerk sign-in URL
        # This would typically be handled by Clerk's frontend SDK
        base_url = "https://auth.brasilito.org"
        callback_url = f"{base_url}/auth/callback"
        
        # For demo purposes, return a message explaining the SSO flow
        return {
            "message": f"SSO login with {provider} would be handled by Clerk's frontend SDK",
            "provider": provider,
            "instructions": [
                "In production, this endpoint would redirect to Clerk's hosted sign-in",
                "Or trigger Clerk's frontend SDK to show the sign-in modal",
                "After successful authentication, Clerk would redirect back with a JWT",
                "That JWT would then be exchanged via the POST /auth/login endpoint"
            ],
            "next_steps": "Integrate Clerk's frontend SDK in the landing page HTML",
            "test_workaround": f"{base_url}/test-login to simulate successful authentication"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSO initiation failed: {str(e)}")

@router.get("/callback")
async def sso_callback(request: Request):
    """
    Handle SSO callback from Clerk
    """
    # This would handle the callback from Clerk after successful authentication
    # For now, return instructions
    return {
        "message": "SSO callback endpoint - would handle Clerk authentication response",
        "query_params": dict(request.query_params),
        "instructions": "This endpoint would process the Clerk callback and redirect to the landing page"
    }