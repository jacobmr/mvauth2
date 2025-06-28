from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
from typing import Optional, List
from models.user import CommunityUser, UserRole
from models.audit import AuditLog
from datetime import datetime

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[CommunityUser]:
        """Get user by internal ID"""
        result = await self.db.execute(select(CommunityUser).where(CommunityUser.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_clerk_id(self, clerk_user_id: str) -> Optional[CommunityUser]:
        """Get user by Clerk user ID"""
        result = await self.db.execute(
            select(CommunityUser).where(CommunityUser.clerk_user_id == clerk_user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[CommunityUser]:
        """Get user by email"""
        result = await self.db.execute(select(CommunityUser).where(CommunityUser.email == email))
        return result.scalar_one_or_none()

    async def create(
        self,
        clerk_user_id: str,
        email: str,
        full_name: str,
        unit_number: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: UserRole = UserRole.HOMEOWNER
    ) -> CommunityUser:
        """Create a new community user"""
        user = CommunityUser(
            clerk_user_id=clerk_user_id,
            email=email,
            full_name=full_name,
            unit_number=unit_number,
            phone_number=phone_number,
            role=role
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_by_clerk_id(
        self,
        clerk_user_id: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        unit_number: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> Optional[CommunityUser]:
        """Update user by Clerk ID"""
        
        update_data = {"updated_at": datetime.utcnow()}
        if email is not None:
            update_data["email"] = email
        if full_name is not None:
            update_data["full_name"] = full_name
        if unit_number is not None:
            update_data["unit_number"] = unit_number
        if phone_number is not None:
            update_data["phone_number"] = phone_number
        if role is not None:
            update_data["role"] = role
        if is_active is not None:
            update_data["is_active"] = is_active

        await self.db.execute(
            update(CommunityUser)
            .where(CommunityUser.clerk_user_id == clerk_user_id)
            .values(**update_data)
        )
        await self.db.commit()
        
        return await self.get_by_clerk_id(clerk_user_id)

    async def update_last_login(self, clerk_user_id: str) -> None:
        """Update user's last login timestamp"""
        await self.db.execute(
            update(CommunityUser)
            .where(CommunityUser.clerk_user_id == clerk_user_id)
            .values(last_login=datetime.utcnow())
        )
        await self.db.commit()

    async def get_all_active_users(self) -> List[CommunityUser]:
        """Get all active community users"""
        result = await self.db.execute(
            select(CommunityUser).where(CommunityUser.is_active == True)
        )
        return result.scalars().all()

    async def get_users_by_role(self, role: UserRole) -> List[CommunityUser]:
        """Get users by role"""
        result = await self.db.execute(
            select(CommunityUser).where(CommunityUser.role == role)
        )
        return result.scalars().all()

    async def deactivate_user(self, clerk_user_id: str) -> Optional[CommunityUser]:
        """Deactivate a user"""
        return await self.update_by_clerk_id(clerk_user_id, is_active=False)

    async def log_user_action(
        self,
        user_id: Optional[int],
        service_name: str,
        action: str,
        resource: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        extra_data: Optional[str] = None
    ) -> AuditLog:
        """Log user action for audit trail"""
        log = AuditLog(
            user_id=user_id,
            service_name=service_name,
            action=action,
            resource=resource,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data
        )
        
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log