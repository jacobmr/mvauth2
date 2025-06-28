from datetime import datetime, timedelta
from typing import Dict, Optional
from jose import jwt
from fastapi import HTTPException
from utils.config import settings

class JWTService:
    @staticmethod
    def create_community_token(user_data: Dict) -> str:
        """Create a JWT token for community services"""
        payload = {
            "user_id": user_data["id"],
            "clerk_user_id": user_data["clerk_user_id"],
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "role": user_data["role"],
            "unit_number": user_data.get("unit_number"),
            "is_active": user_data["is_active"],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
            "iss": "community-auth-service",
            "type": "community_access"
        }
        
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def validate_token(token: str) -> Dict:
        """Validate and decode a community JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": True}
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        """Create a refresh token for longer-term authentication"""
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=30),  # 30 days
            "iss": "community-auth-service"
        }
        
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def validate_refresh_token(token: str) -> Dict:
        """Validate a refresh token"""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": True}
            )
            
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Invalid token type")
                
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")