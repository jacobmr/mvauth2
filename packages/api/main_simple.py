from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from typing import Optional
import jwt
import json
from sqlalchemy.ext.asyncio import AsyncSession
from utils.database import get_db, init_db
from repositories.user_repository import UserRepository
from models.user import UserRole
from contextlib import asynccontextmanager

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    try:
        await init_db()
        print("Database initialization completed")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        # Continue without database - will show appropriate errors
    yield

app = FastAPI(
    title="MVAuth2 Service",
    description="Centralized authentication service for multiple applications, starting with ARC project",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api")
async def api_status():
    return {"service": "MVAuth2 Service", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "MVAuth2 API is running", "docs": "/docs"}

@app.get("/api/apps")
async def get_apps(authorization: Optional[str] = Header(None), x_user_email: Optional[str] = Header(None)):
    """Get applications available to the authenticated user"""
    user_email = "user@example.com"  # Default
    user_role = "USER"
    user_name = "Demo User"
    
    print(f"=== DEBUG INFO ===")
    print(f"Authorization header present: {bool(authorization)}")
    print(f"X-User-Email header: {x_user_email}")
    
    # Extract user info from Clerk JWT token if available
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.replace("Bearer ", "")
            # For now, we'll decode without verification (in production, verify with Clerk's public key)
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Try multiple ways to get email from Clerk token
            user_email = (
                decoded.get("email") or 
                decoded.get("primary_email_address_id") or 
                (decoded.get("email_addresses", [{}])[0].get("email_address") if decoded.get("email_addresses") else None) or
                decoded.get("email_address") or
                decoded.get("preferred_username") or
                user_email
            )
            
            # If still no email, try to get user ID and note it
            user_id = decoded.get("sub")
            if not user_email and user_id:
                print(f"No email found in token, but have user ID: {user_id}")
                # For now, hardcode jacob's user check using a different method
                # In production, you'd call Clerk's API to get user details by ID
            
            # Try multiple ways to get name
            first_name = decoded.get("first_name", "")
            last_name = decoded.get("last_name", "")
            user_name = (
                decoded.get("name") or 
                decoded.get("full_name") or 
                f"{first_name} {last_name}".strip() or
                user_name
            )
            
            print(f"Decoded token: email='{user_email}', name='{user_name}'")
            print(f"All token keys: {list(decoded.keys())}")
            
        except Exception as e:
            print(f"Token decode error: {e}")
            print(f"Token content: {token[:50]}...")
    
    # Also check the X-User-Email header (fallback for development keys)
    if x_user_email:
        print(f"Found email in header: {x_user_email}")
        if not user_email or user_email == "user@example.com":
            user_email = x_user_email
            print(f"Using email from header: {user_email}")
    else:
        print("No email in X-User-Email header")
    
    # Check if user is superadmin
    print(f"Final email check: '{user_email}' == 'jacob@reider.us' ? {user_email == 'jacob@reider.us'}")
    if user_email == "jacob@reider.us":
        user_role = "SUPER_ADMIN"
        user_name = "Jacob Reider"
    
    # Base applications available to all users
    applications = [
        {
            "name": "Architecture Review",
            "description": "Architecture Review Committee platform",
            "url": "https://arc.brasilito.org",
            "roles": ["USER", "SUPER_ADMIN"]
        }
    ]
    
    # Add admin applications for superadmin
    if user_role == "SUPER_ADMIN":
        applications.append({
            "name": "User Management",
            "description": "Manage Mar Vista users and permissions",
            "url": "https://web.brasilito.org/admin",
            "roles": ["SUPER_ADMIN"],
            "admin": True
        })
    
    return {
        "user": {
            "id": user_email.replace("@", "_").replace(".", "_"),
            "email": user_email,
            "full_name": user_name,
            "role": user_role
        },
        "applications": applications,
        "total_access": len(applications)
    }

# REMOVED: HTML admin interface moved to web project
# This API should only serve JSON endpoints

@app.get("/admin/api/users")
async def admin_get_users(
    authorization: Optional[str] = Header(None), 
    x_user_email: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all users - admin only"""
    user_email = x_user_email or "user@example.com"
    
    if user_email != "jacob@reider.us":
        return {"error": "Unauthorized"}
    
    try:
        users = await UserRepository.get_all_users(db)
        user_dicts = []
        
        for user in users:
            user_dict = user.to_dict()
            # Convert status from is_active boolean to active/inactive string
            user_dict["status"] = "active" if user.is_active else "inactive"
            user_dicts.append(user_dict)
        
        return {
            "users": user_dicts,
            "total": len(user_dicts)
        }
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}

@app.post("/admin/api/users")
async def admin_add_user(
    user_data: dict, 
    authorization: Optional[str] = Header(None), 
    x_user_email: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Add new user - admin only"""
    user_email = x_user_email or "user@example.com"
    
    if user_email != "jacob@reider.us":
        return {"error": "Unauthorized"}
    
    try:
        # Validate required fields
        if not user_data.get("email"):
            return {"error": "Email is required"}
        
        # Check if user already exists
        existing_user = await UserRepository.get_user_by_email(db, user_data["email"])
        if existing_user:
            return {"error": "User with this email already exists"}
        
        # Parse role
        role_str = user_data.get("role", "USER")
        try:
            role = UserRole(role_str)
        except ValueError:
            return {"error": f"Invalid role: {role_str}"}
        
        # Create user (without Clerk ID for now - this will be added when they first login)
        user = await UserRepository.create_user(
            db=db,
            clerk_user_id="",  # Will be filled when user first logs in
            email=user_data["email"],
            full_name=user_data.get("full_name", user_data["email"]),
            role=role
        )
        
        return {
            "success": True,
            "user": user.to_dict()
        }
        
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}

@app.post("/admin/api/user-roles")
async def admin_update_user_roles(
    role_data: dict, 
    authorization: Optional[str] = Header(None), 
    x_user_email: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Update user roles for specific apps - admin only"""
    user_email = x_user_email or "user@example.com"
    
    if user_email != "jacob@reider.us":
        return {"error": "Unauthorized"}
    
    target_email = role_data.get("email")
    app = role_data.get("app")  # 'arc' or 'qr'
    role = role_data.get("role")  # for arc: owner, reviewer, admin; for qr: admin, scanner, owner, guest
    
    if not all([target_email, app, role]):
        return {"error": "Missing required fields: email, app, role"}
    
    # Validate roles
    valid_roles = {
        "arc": ["owner", "reviewer", "admin"],
        "qr": ["admin", "scanner", "owner", "guest"]
    }
    
    if app not in valid_roles or role not in valid_roles[app]:
        return {"error": f"Invalid role '{role}' for app '{app}'. Valid roles: {valid_roles[app]}"}
    
    try:
        # Find user by email
        user = await UserRepository.get_user_by_email(db, target_email)
        if not user:
            return {"error": f"User with email {target_email} not found"}
        
        # Set the app role
        await UserRepository.set_user_app_role(db, user.id, app, role)
        
        return {
            "success": True,
            "user": {"email": target_email},
            "app": app,
            "role": role,
            "updated_by": user_email
        }
        
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}

@app.get("/api/debug")
async def debug_user(authorization: Optional[str] = Header(None)):
    """Debug endpoint to check user authentication"""
    debug_info = {
        "has_auth_header": bool(authorization),
        "auth_header_preview": authorization[:50] + "..." if authorization else None,
        "timestamp": str(os.getenv("TIMESTAMP", "not_set"))
    }
    
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.replace("Bearer ", "")
            decoded = jwt.decode(token, options={"verify_signature": False})
            debug_info["decoded_token"] = decoded
            debug_info["all_token_keys"] = list(decoded.keys())
            debug_info["email_from_token"] = decoded.get("email") or decoded.get("primary_email_address_id") or (decoded.get("email_addresses", [{}])[0].get("email_address") if decoded.get("email_addresses") else None)
            
            # Try to extract from sub claim which might contain user ID
            if "sub" in decoded:
                debug_info["sub_claim"] = decoded["sub"]
                
            # Check all possible email fields
            debug_info["possible_emails"] = {
                "email": decoded.get("email"),
                "primary_email": decoded.get("primary_email_address_id"),
                "email_addresses": decoded.get("email_addresses"),
                "sub": decoded.get("sub"),
                "email_verified": decoded.get("email_verified"),
                "preferred_username": decoded.get("preferred_username")
            }
        except Exception as e:
            debug_info["decode_error"] = str(e)
    
    return debug_info

@app.put("/admin/api/users")
async def admin_update_user(
    user_data: dict, 
    authorization: Optional[str] = Header(None), 
    x_user_email: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Update existing user - admin only"""
    user_email = x_user_email or "user@example.com"
    
    if user_email != "jacob@reider.us":
        return {"error": "Unauthorized"}
    
    try:
        user_id = user_data.get("id")
        if not user_id:
            return {"error": "User ID is required"}
        
        # Parse role if provided
        role = None
        if user_data.get("role"):
            try:
                role = UserRole(user_data["role"])
            except ValueError:
                return {"error": f"Invalid role: {user_data['role']}"}
        
        # Parse status
        is_active = None
        if user_data.get("status"):
            is_active = user_data["status"] == "active"
        
        # Update user
        updated_user = await UserRepository.update_user(
            db=db,
            user_id=int(user_id),
            email=user_data.get("email"),
            full_name=user_data.get("full_name"),
            role=role,
            is_active=is_active
        )
        
        if not updated_user:
            return {"error": "User not found"}
        
        return {
            "success": True,
            "user": updated_user.to_dict()
        }
        
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}

@app.delete("/admin/api/users/{user_id}")
async def admin_delete_user(
    user_id: str, 
    authorization: Optional[str] = Header(None), 
    x_user_email: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Delete user - admin only"""
    user_email = x_user_email or "user@example.com"
    
    if user_email != "jacob@reider.us":
        return {"error": "Unauthorized"}
    
    try:
        # Soft delete (set is_active = False)
        success = await UserRepository.delete_user(db, int(user_id))
        
        if not success:
            return {"error": "User not found"}
        
        return {
            "success": True,
            "message": f"User {user_id} deleted successfully",
            "deleted_by": user_email
        }
        
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}

