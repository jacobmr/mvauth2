from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from utils.database import Base
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("community_users.id"), nullable=True)
    service_name = Column(String(100), nullable=False)  # "qr_gate", "amenity_booking", etc.
    action = Column(String(100), nullable=False)  # "login", "access_granted", "permission_changed"
    resource = Column(String(255), nullable=True)  # What was accessed/modified
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON string for additional context
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("CommunityUser")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "service_name": self.service_name,
            "action": self.action,
            "resource": self.resource,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "extra_data": self.extra_data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user": self.user.to_dict() if self.user else None
        }