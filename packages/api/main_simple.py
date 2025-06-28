from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv
from typing import Optional
import jwt
import json

load_dotenv()

app = FastAPI(
    title="MVAuth2 Service",
    description="Centralized authentication service for multiple applications, starting with ARC project",
    version="1.0.0"
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
            "url": f"{os.getenv('NEXT_PUBLIC_COMMUNITY_AUTH_API', 'https://auth.brasilito.org')}/admin/users",
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

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(authorization: Optional[str] = Header(None), x_user_email: Optional[str] = Header(None)):
    """User management interface for superadmins"""
    user_email = "user@example.com"
    
    print(f"=== ADMIN DEBUG INFO ===")
    print(f"Authorization header present: {bool(authorization)}")
    print(f"X-User-Email header: {x_user_email}")
    
    # Extract user info from Clerk JWT token if available
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.replace("Bearer ", "")
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_email = (
                decoded.get("email") or 
                decoded.get("primary_email_address_id") or 
                (decoded.get("email_addresses", [{}])[0].get("email_address") if decoded.get("email_addresses") else None) or
                decoded.get("email_address") or
                decoded.get("preferred_username") or
                user_email
            )
            print(f"Email from token: {user_email}")
        except Exception as e:
            print(f"Token decode error: {e}")
    
    # Also check the X-User-Email header (fallback)
    if x_user_email:
        print(f"Found email in header: {x_user_email}")
        if not user_email or user_email == "user@example.com":
            user_email = x_user_email
            print(f"Using email from header: {user_email}")
    
    print(f"Final admin email check: '{user_email}' == 'jacob@reider.us' ? {user_email == 'jacob@reider.us'}")
    
    # Verify superadmin access
    if user_email != "jacob@reider.us":
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Access Denied - Mar Vista</title></head>
        <body style="font-family: system-ui; text-align: center; padding: 50px;">
            <h1>🚫 Access Denied</h1>
            <p>Superadmin access required.</p>
            <p>Current user: {user_email}</p>
            <p><a href="https://web.brasilito.org">← Back to Mar Vista Portal</a></p>
        </body>
        </html>
        """
    
    # Return basic user management HTML page
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>User Management - Mar Vista</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #333; margin-bottom: 20px; }
            .admin-section { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 6px; }
            .btn { background: #0066cc; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
            .btn:hover { background: #0052a3; }
            .info { background: #e7f3ff; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌴 Mar Vista User Management</h1>
            
            <div class="info">
                <strong>Superadmin:</strong> jacob@reider.us<br>
                <strong>System:</strong> MVAuth2 Centralized Authentication
            </div>
            
            <div class="admin-section">
                <h2>User Management</h2>
                <p>Manage users across all Mar Vista applications</p>
                <button class="btn" onclick="viewUsers()">View All Users</button>
                <button class="btn" onclick="addUser()">Add New User</button>
                <button class="btn" onclick="bulkOps()">Bulk Operations</button>
            </div>
            
            <div class="admin-section">
                <h2>Application Access Control</h2>
                <p>Manage user permissions for different applications</p>
                <button class="btn" onclick="manageArcAccess()">Architecture Review Access</button>
                <button class="btn" onclick="managePermissions()">Permission Templates</button>
            </div>
            
            <div class="admin-section">
                <h2>System Information</h2>
                <p>Current system status and configuration</p>
                <button class="btn" onclick="window.open('/api', '_blank')">API Status</button>
                <button class="btn" onclick="window.open('/docs', '_blank')">API Documentation</button>
            </div>
            
            <div style="margin-top: 30px; text-align: center; color: #666;">
                <p><a href="https://web.brasilito.org" style="color: #0066cc;">← Back to Mar Vista Portal</a></p>
            </div>
        </div>
        
        <script>
            // Get auth info from URL parameters (passed by the frontend)
            const urlParams = new URLSearchParams(window.location.search);
            const authToken = urlParams.get('token');
            const userEmail = urlParams.get('email');
            
            function makeAuthenticatedRequest(url, options = {}) {
                const headers = {
                    'Content-Type': 'application/json',
                    'X-User-Email': userEmail || '',
                    ...options.headers
                };
                
                if (authToken) {
                    headers['Authorization'] = `Bearer ${authToken}`;
                }
                
                return fetch(url, {
                    ...options,
                    headers
                });
            }
            
            function viewUsers() {
                makeAuthenticatedRequest('/admin/api/users')
                    .then(r => r.json())
                    .then(data => {
                        if (data.error) {
                            alert('Error: ' + data.error);
                            return;
                        }
                        
                        let userList = 'Current Users:\\n\\n';
                        data.users.forEach(user => {
                            userList += `Email: ${user.email}\\n`;
                            userList += `Role: ${user.role}\\n`;
                            userList += `Status: ${user.status}\\n`;
                            if (user.app_roles) {
                                userList += `App Roles: ${JSON.stringify(user.app_roles)}\\n`;
                            }
                            userList += '---\\n';
                        });
                        userList += `\\nTotal: ${data.total} users`;
                        alert(userList);
                    })
                    .catch(e => alert('Error: ' + e.message));
            }
            
            function addUser() {
                const email = prompt('Enter user email to add:');
                if (!email) return;
                
                const role = prompt('Enter role (USER, ADMIN, SUPER_ADMIN):', 'USER');
                if (!role) return;
                
                makeAuthenticatedRequest('/admin/api/users', {
                    method: 'POST',
                    body: JSON.stringify({email: email, role: role})
                })
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        alert('Error: ' + data.error);
                    } else {
                        alert(`User added successfully:\\n${data.user.email} (${data.user.role})`);
                    }
                })
                .catch(e => alert('Error: ' + e.message));
            }
            
            function manageArcAccess() {
                makeAuthenticatedRequest('/admin/api/users')
                    .then(r => r.json())
                    .then(data => {
                        if (data.error) {
                            alert('Error: ' + data.error);
                            return;
                        }
                        
                        const email = prompt('Enter user email to manage ARC access:');
                        if (!email) return;
                        
                        const role = prompt('Enter ARC role (owner, reviewer, admin):', 'reviewer');
                        if (!role) return;
                        
                        return makeAuthenticatedRequest('/admin/api/user-roles', {
                            method: 'POST',
                            body: JSON.stringify({
                                email: email,
                                app: 'arc',
                                role: role
                            })
                        });
                    })
                    .then(r => r ? r.json() : null)
                    .then(data => {
                        if (data) {
                            if (data.error) {
                                alert('Error: ' + data.error);
                            } else {
                                alert(`ARC role updated successfully:\\n${data.user.email} is now ${data.role} in ARC`);
                            }
                        }
                    })
                    .catch(e => alert('Error: ' + e.message));
            }
            
            function bulkOps() {
                alert('Bulk operations: Export users, bulk role changes, etc.\\nComing soon!');
            }
            
            function managePermissions() {
                alert('Permission Templates Management\\nComing soon!');
            }
        </script>
    </body>
    </html>
    """

@app.get("/admin/api/users")
async def admin_get_users(authorization: Optional[str] = Header(None), x_user_email: Optional[str] = Header(None)):
    """Get all users - admin only"""
    user_email = x_user_email or "user@example.com"
    
    if user_email != "jacob@reider.us":
        return {"error": "Unauthorized"}
    
    # Mock user data with app-specific roles - in production this would query your user database
    return {
        "users": [
            {
                "id": "1", 
                "email": "jacob@reider.us", 
                "role": "SUPER_ADMIN", 
                "status": "active",
                "app_roles": {
                    "arc": "owner",
                    "qr": "admin"
                }
            },
            {
                "id": "2", 
                "email": "user@example.com", 
                "role": "USER", 
                "status": "active",
                "app_roles": {
                    "arc": "reviewer"
                }
            },
            {
                "id": "3", 
                "email": "demo@brasilito.org", 
                "role": "USER", 
                "status": "active",
                "app_roles": {
                    "arc": "admin"
                }
            },
        ],
        "total": 3
    }

@app.post("/admin/api/users")
async def admin_add_user(user_data: dict, authorization: Optional[str] = Header(None), x_user_email: Optional[str] = Header(None)):
    """Add new user - admin only"""
    user_email = x_user_email or "user@example.com"
    
    if user_email != "jacob@reider.us":
        return {"error": "Unauthorized"}
    
    # Mock user creation - in production this would create the user
    return {
        "success": True,
        "user": {
            "id": "new_" + str(hash(user_data.get("email", ""))),
            "email": user_data.get("email"),
            "role": user_data.get("role", "USER"),
            "status": "active",
            "created_by": user_email
        }
    }

@app.post("/admin/api/user-roles")
async def admin_update_user_roles(role_data: dict, authorization: Optional[str] = Header(None), x_user_email: Optional[str] = Header(None)):
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
    
    # Mock role update - in production this would update your user database
    print(f"Updating user {target_email} to role {role} in app {app}")
    
    return {
        "success": True,
        "user": {"email": target_email},
        "app": app,
        "role": role,
        "updated_by": user_email
    }

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