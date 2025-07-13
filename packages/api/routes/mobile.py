from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json
import base64

from utils.database import get_db
from services.jwt_service import JWTService
from repositories.user_repository import UserRepository
from models.user import UserRole
from routes.users import get_current_user

router = APIRouter()
security = HTTPBearer()

class QRGenerationRequest(BaseModel):
    visitor_name: str
    access_duration: int  # hours
    access_type: str  # 'one-time' or 'recurring'
    notes: Optional[str] = None

class QRCodeResponse(BaseModel):
    qr_code: str
    expiration_time: str
    visitor_name: str
    unit_number: Optional[str]
    resident_name: str

class AccessLogEntry(BaseModel):
    id: str
    timestamp: str
    type: str  # 'entry' or 'exit'
    method: str  # 'proximity', 'qr', 'manual'
    location: str
    visitor_name: Optional[str] = None

@router.post("/qr/generate", response_model=QRCodeResponse)
async def generate_qr_code(
    qr_request: QRGenerationRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate QR code for visitor access"""
    
    # Calculate expiration time
    expiration_time = datetime.utcnow() + timedelta(hours=qr_request.access_duration)
    
    # Create QR payload
    qr_payload = {
        "type": "visitor_access",
        "visitor_name": qr_request.visitor_name.strip(),
        "unit_number": current_user.unit_number,
        "resident_name": current_user.full_name,
        "resident_id": current_user.id,
        "access_type": qr_request.access_type,
        "expiration_time": expiration_time.isoformat(),
        "notes": qr_request.notes.strip() if qr_request.notes else "",
        "community_id": "mar-vista",
        "generated_at": datetime.utcnow().isoformat(),
        "generated_by": current_user.id,
    }
    
    # TODO: Implement actual encryption using Fernet (like existing QR system)
    # For Phase 1, use base64 encoding
    qr_string = base64.b64encode(json.dumps(qr_payload).encode()).decode()
    
    # TODO: Log QR generation to access logs
    user_repo = UserRepository(db)
    await user_repo.log_user_action(
        user_id=current_user.id,
        service_name="qr_guardian_mobile",
        action="qr_generated",
        resource=f"visitor:{qr_request.visitor_name}",
        extra_data=f"Generated QR for {qr_request.visitor_name}, expires: {expiration_time.isoformat()}"
    )
    
    return QRCodeResponse(
        qr_code=qr_string,
        expiration_time=expiration_time.isoformat(),
        visitor_name=qr_request.visitor_name,
        unit_number=current_user.unit_number,
        resident_name=current_user.full_name
    )

@router.get("/access-history", response_model=List[AccessLogEntry])
async def get_access_history(
    limit: int = 50,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's access history"""
    
    # TODO: Implement actual access log retrieval
    # For Phase 1, return mock data based on user ID
    mock_entries = [
        AccessLogEntry(
            id=f"entry_{current_user.id}_1",
            timestamp=(datetime.utcnow() - timedelta(hours=2)).isoformat(),
            type="entry",
            method="proximity",
            location="Main Gate"
        ),
        AccessLogEntry(
            id=f"exit_{current_user.id}_1", 
            timestamp=(datetime.utcnow() - timedelta(hours=6)).isoformat(),
            type="exit",
            method="proximity",
            location="Main Gate"
        )
    ]
    
    return mock_entries[:limit]

@router.post("/access/log")
async def log_access_event(
    access_type: str,  # 'entry' or 'exit'
    method: str,       # 'proximity', 'qr', 'manual'
    location: str = "Main Gate",
    visitor_name: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Log an access event (for proximity detection)"""
    
    user_repo = UserRepository(db)
    
    # Log the access event
    extra_data = f"Access {access_type} via {method} at {location}"
    if visitor_name:
        extra_data += f" for visitor: {visitor_name}"
    
    await user_repo.log_user_action(
        user_id=current_user.id,
        service_name="qr_guardian_mobile",
        action=f"access_{access_type}",
        resource=f"gate:{location}",
        extra_data=extra_data
    )
    
    return {"message": "Access event logged successfully"}

@router.get("/health")
async def mobile_health_check():
    """Health check endpoint for mobile app"""
    return {
        "status": "healthy",
        "service": "qr_guardian_mobile_api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }