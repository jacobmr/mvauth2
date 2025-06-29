from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from models.user import CommunityUser, UserAppRole, UserRole
from typing import List, Optional, Dict

class UserRepository:
    
    @staticmethod
    async def get_all_users(db: AsyncSession) -> List[CommunityUser]:
        """Get all users with their app roles"""
        result = await db.execute(
            select(CommunityUser)
            .options(selectinload(CommunityUser.app_roles))
            .where(CommunityUser.is_active == True)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[CommunityUser]:
        """Get user by ID with app roles"""
        result = await db.execute(
            select(CommunityUser)
            .options(selectinload(CommunityUser.app_roles))
            .where(CommunityUser.id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[CommunityUser]:
        """Get user by email with app roles"""
        result = await db.execute(
            select(CommunityUser)
            .options(selectinload(CommunityUser.app_roles))
            .where(CommunityUser.email == email)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_clerk_id(db: AsyncSession, clerk_user_id: str) -> Optional[CommunityUser]:
        """Get user by Clerk user ID with app roles"""
        result = await db.execute(
            select(CommunityUser)
            .options(selectinload(CommunityUser.app_roles))
            .where(CommunityUser.clerk_user_id == clerk_user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(
        db: AsyncSession, 
        clerk_user_id: str,
        email: str,
        full_name: str,
        role: UserRole = UserRole.USER,
        unit_number: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> CommunityUser:
        """Create a new user"""
        user = CommunityUser(
            clerk_user_id=clerk_user_id,
            email=email,
            full_name=full_name,
            role=role,
            unit_number=unit_number,
            phone_number=phone_number,
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: int,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[UserRole] = None,
        unit_number: Optional[str] = None,
        phone_number: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[CommunityUser]:
        """Update user information"""
        user = await UserRepository.get_user_by_id(db, user_id)
        if not user:
            return None
        
        if email is not None:
            user.email = email
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if unit_number is not None:
            user.unit_number = unit_number
        if phone_number is not None:
            user.phone_number = phone_number
        if is_active is not None:
            user.is_active = is_active
        
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> bool:
        """Soft delete user (set is_active = False)"""
        user = await UserRepository.get_user_by_id(db, user_id)
        if not user:
            return False
        
        user.is_active = False
        await db.commit()
        return True
    
    @staticmethod
    async def hard_delete_user(db: AsyncSession, user_id: int) -> bool:
        """Hard delete user and all related data"""
        # Delete app roles first
        await db.execute(delete(UserAppRole).where(UserAppRole.user_id == user_id))
        
        # Delete user
        result = await db.execute(delete(CommunityUser).where(CommunityUser.id == user_id))
        await db.commit()
        
        return result.rowcount > 0
    
    @staticmethod
    async def set_user_app_role(
        db: AsyncSession,
        user_id: int,
        app_name: str,
        role: str
    ) -> bool:
        """Set or update user's role for a specific app"""
        # First, remove existing role for this app
        await db.execute(
            delete(UserAppRole)
            .where(UserAppRole.user_id == user_id)
            .where(UserAppRole.app_name == app_name)
        )
        
        # Add new role
        app_role = UserAppRole(
            user_id=user_id,
            app_name=app_name,
            role=role
        )
        
        db.add(app_role)
        await db.commit()
        return True
    
    @staticmethod
    async def remove_user_app_role(
        db: AsyncSession,
        user_id: int,
        app_name: str
    ) -> bool:
        """Remove user's role for a specific app"""
        result = await db.execute(
            delete(UserAppRole)
            .where(UserAppRole.user_id == user_id)
            .where(UserAppRole.app_name == app_name)
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def get_users_by_app_role(
        db: AsyncSession,
        app_name: str,
        role: Optional[str] = None
    ) -> List[CommunityUser]:
        """Get all users with access to a specific app, optionally filtered by role"""
        query = (
            select(CommunityUser)
            .options(selectinload(CommunityUser.app_roles))
            .join(UserAppRole)
            .where(UserAppRole.app_name == app_name)
            .where(CommunityUser.is_active == True)
        )
        
        if role:
            query = query.where(UserAppRole.role == role)
        
        result = await db.execute(query)
        return result.scalars().all()