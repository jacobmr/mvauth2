# Community Auth Service

Centralized authentication service for community applications using Clerk.com SSO.

## Features

- **Clerk.com SSO Integration**: Google, Apple, email authentication
- **JWT Token Management**: Secure service-to-service communication
- **Role-Based Access Control**: Resident, Admin, Staff, Guest roles
- **Audit Logging**: Track all authentication and authorization events
- **Community Management**: User profiles, announcements, statistics

## Quick Start

### 1. Environment Setup

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Development Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication
- `POST /auth/login` - Exchange Clerk JWT for Community token
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (logging only)
- `GET /auth/profile` - Get current user profile

### Token Validation (Service-to-Service)
- `POST /validate/token` - Validate user token for services
- `GET /validate/user/{user_id}` - Get user data for services
- `POST /validate/permissions` - Check user permissions

### User Management
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update current user profile
- `GET /users/community` - List community members (admin)
- `POST /users/{user_id}/role` - Assign user role (admin)
- `POST /users/{user_id}/deactivate` - Deactivate user (admin)

### Community
- `GET /community/info` - Community information and stats
- `GET /community/members` - Active community members list
- `POST /community/announcements` - Send announcements (admin)

## Deployment

### Vercel + Supabase (Recommended)

1. **Set up Supabase Database**:
   - Go to [supabase.com](https://supabase.com)
   - Create new project
   - Get your connection string

2. **Deploy to Vercel**:
   ```bash
   vercel --prod
   ```

3. **Set Environment Variables in Vercel**:
   - `DATABASE_URL` (from Supabase)
   - `CLERK_PUBLISHABLE_KEY`
   - `CLERK_SECRET_KEY`
   - `JWT_SECRET_KEY`
   - `SERVICE_TOKEN`
   - `COMMUNITY_NAME`
   - `ADMIN_EMAILS`

### Alternative: Self-Hosted

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run with gunicorn
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Integration with Other Services

### QR Gate Service Integration

The QR Gate Service should validate tokens like this:

```python
import httpx

async def validate_user_token(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://your-auth-service.vercel.app/validate/token",
            json={
                "token": token,
                "service_name": "qr_gate"
            }
        )
        return response.json()
```

### Service-to-Service Authentication

For secure service-to-service calls, use the service token:

```python
headers = {
    "X-Service-Token": "your-service-token",
    "X-Service-Name": "qr_gate"
}

response = await client.get(
    "https://your-auth-service.vercel.app/validate/user/123",
    headers=headers
)
```

## Development

### Project Structure

```
community-auth-service/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── vercel.json            # Vercel deployment configuration
├── models/
│   ├── user.py            # User and role models
│   └── audit.py           # Audit logging models
├── routes/
│   ├── auth.py            # Authentication endpoints
│   ├── validation.py      # Token validation endpoints
│   ├── users.py           # User management endpoints
│   └── community.py       # Community features
├── services/
│   ├── clerk_service.py   # Clerk.com integration
│   └── jwt_service.py     # JWT token management
├── repositories/
│   └── user_repository.py # Database operations
└── utils/
    ├── config.py          # Configuration management
    └── database.py        # Database connection
```

### Adding New Services

1. Update the service validation in `routes/validation.py`
2. Add service-specific permissions in `models/user.py`
3. Update audit logging to track the new service

## Security Considerations

- Always use HTTPS in production
- Rotate JWT secret keys regularly
- Monitor audit logs for suspicious activity
- Use strong service tokens for inter-service communication
- Keep Clerk keys secure and never commit them to version control

## Monitoring

The service provides several endpoints for monitoring:
- `GET /health` - Health check
- `GET /community/stats` - Usage statistics (admin only)
- Audit logs track all authentication events