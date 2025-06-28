from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from utils.database import Base
import enum
from datetime import datetime
from typing import List, Optional

class UserRole(str, enum.Enum):
    # Community-wide roles
    SUPER_ADMIN = "super_admin"
    HOMEOWNER = "homeowner"
    GUEST = "guest"
    
    # ARC Application roles
    ARC_ADMIN = "arc_admin"
    ARC_REVIEWER = "arc_reviewer"
    
    # QR Gate Application roles  
    QR_ADMIN = "qr_admin"
    QR_SCANNER = "qr_scanner"
    
    # Legacy roles (for migration)
    RESIDENT = "resident"  # Maps to HOMEOWNER
    ADMIN = "admin"        # Maps to SUPER_ADMIN
    STAFF = "staff"        # Maps to QR_SCANNER

class CommunityUser(Base):
    __tablename__ = "community_users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    unit_number = Column(String(50), nullable=True)
    phone_number = Column(String(50), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.HOMEOWNER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships will be added as needed for audit logs, permissions, etc.

    def get_permissions_for_service(self, service_name: str) -> List[str]:
        """Get user permissions for a specific service"""
        
        # Super admin has access to everything
        if self.role == UserRole.SUPER_ADMIN or self.role == UserRole.ADMIN:  # Legacy mapping
            return ["access", "admin", "manage_users", "view_logs", "super_admin"]
        
        # Service-specific permissions
        if service_name == "arc":
            return self._get_arc_permissions()
        elif service_name == "qr_gate":
            return self._get_qr_permissions()
        elif service_name == "community_auth":
            return self._get_community_permissions()
        else:
            # Default permissions for unknown services
            return self._get_default_permissions()
    
    def _get_arc_permissions(self) -> List[str]:
        """Get permissions for ARC application system"""
        base = ["access"]
        
        if self.role == UserRole.ARC_ADMIN:
            return base + ["admin", "manage_applications", "assign_reviewers", "view_all"]
        elif self.role == UserRole.ARC_REVIEWER:
            return base + ["review", "comment", "approve", "deny"]
        elif self.role in [UserRole.HOMEOWNER, UserRole.RESIDENT]:  # Legacy mapping
            return base + ["submit", "view_own"]
        else:
            return ["guest"]
    
    def _get_qr_permissions(self) -> List[str]:
        """Get permissions for QR Gate system"""
        base = ["access"]
        
        if self.role == UserRole.QR_ADMIN:
            return base + ["admin", "manage_gates", "view_logs", "manage_devices"]
        elif self.role == UserRole.QR_SCANNER or self.role == UserRole.STAFF:  # Legacy mapping
            return base + ["scan", "validate", "open_gate"]
        elif self.role in [UserRole.HOMEOWNER, UserRole.RESIDENT]:  # Legacy mapping
            return base + ["resident_access"]
        else:
            return ["guest"]
    
    def _get_community_permissions(self) -> List[str]:
        """Get permissions for community auth management"""
        base = ["access"]
        
        if self.role == UserRole.SUPER_ADMIN or self.role == UserRole.ADMIN:  # Legacy
            return base + ["manage_users", "assign_roles", "view_all_logs"]
        else:
            return base + ["view_profile", "update_profile"]
    
    def _get_default_permissions(self) -> List[str]:
        """Default permissions for any service"""
        if self.role == UserRole.GUEST:
            return ["guest"]
        elif self.role in [UserRole.HOMEOWNER, UserRole.RESIDENT]:  # Legacy mapping
            return ["access", "user"]
        else:
            return ["access"]

    def to_dict(self):
        return {
            "id": self.id,
            "clerk_user_id": self.clerk_user_id,
            "email": self.email,
            "full_name": self.full_name,
            "unit_number": self.unit_number,
            "phone_number": self.phone_number,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }