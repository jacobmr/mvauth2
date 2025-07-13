import os
from typing import Dict, Optional
from fastapi import HTTPException
from clerk import Clerk
from utils.config import settings

class ClerkService:
    def __init__(self):
        self.secret_key = settings.clerk_secret_key
        self.publishable_key = settings.clerk_publishable_key
        self.client = Clerk(api_key=self.secret_key, publishable_key=self.publishable_key)

    async def verify_clerk_token(self, token: str) -> Dict:
        """Verify Clerk JWT token and return user info"""
        try:
            # Verify the session token using Clerk's SDK
            session = self.client.sessions.verify_session(token=token)
            
            if not session:
                raise HTTPException(status_code=401, detail="Invalid session token")
            
            # Get user details
            user = self.client.users.get_user(session.user_id)
            
            # Extract user information
            primary_email = None
            if user.email_addresses:
                for email in user.email_addresses:
                    if email.id == user.primary_email_address_id:
                        primary_email = email.email_address
                        break
                # Fallback to first email if primary not found
                if not primary_email and user.email_addresses:
                    primary_email = user.email_addresses[0].email_address
            
            primary_phone = None
            if user.phone_numbers:
                for phone in user.phone_numbers:
                    if phone.id == user.primary_phone_number_id:
                        primary_phone = phone.phone_number
                        break
                # Fallback to first phone if primary not found
                if not primary_phone and user.phone_numbers:
                    primary_phone = user.phone_numbers[0].phone_number
            
            return {
                'clerk_user_id': user.id,
                'email': primary_email,
                'email_verified': bool(primary_email),  # If we have an email, it's verified
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip() or primary_email or user.id,
                'phone_number': primary_phone,
                'phone_verified': bool(primary_phone),
                'issued_at': session.created_at,
                'expires_at': session.expire_at,
            }
            
        except Exception as e:
            if "invalid" in str(e).lower() or "expired" in str(e).lower():
                raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")
            else:
                raise HTTPException(status_code=500, detail=f"Token verification failed: {str(e)}")

    async def get_user_by_id(self, clerk_user_id: str) -> Optional[Dict]:
        """Get user details from Clerk by user ID"""
        try:
            user = self.client.users.get_user(clerk_user_id)
            
            if not user:
                return None
            
            # Extract user information
            primary_email = None
            if user.email_addresses:
                for email in user.email_addresses:
                    if email.id == user.primary_email_address_id:
                        primary_email = email.email_address
                        break
                if not primary_email and user.email_addresses:
                    primary_email = user.email_addresses[0].email_address
            
            primary_phone = None
            if user.phone_numbers:
                for phone in user.phone_numbers:
                    if phone.id == user.primary_phone_number_id:
                        primary_phone = phone.phone_number
                        break
                if not primary_phone and user.phone_numbers:
                    primary_phone = user.phone_numbers[0].phone_number
            
            return {
                'clerk_user_id': user.id,
                'email': primary_email,
                'email_verified': bool(primary_email),
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip() or primary_email or user.id,
                'phone_number': primary_phone,
                'phone_verified': bool(primary_phone),
                'created_at': getattr(user, 'created_at', None),
                'updated_at': getattr(user, 'updated_at', None),
            }
                    
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            else:
                raise HTTPException(status_code=500, detail=f"Failed to fetch user from Clerk: {str(e)}")

    async def create_oauth_signin(self, provider: str) -> Dict:
        """Initialize OAuth sign-in flow"""
        try:
            # Create sign-in attempt with OAuth strategy
            signin_attempt = self.client.sign_ins.create_sign_in(
                strategy=provider
            )
            
            if signin_attempt.first_factor_verification and signin_attempt.first_factor_verification.external_verification_redirect_url:
                return {
                    'success': True,
                    'redirectUrl': signin_attempt.first_factor_verification.external_verification_redirect_url,
                    'signInId': signin_attempt.id
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not initialize OAuth flow - no redirect URL returned'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"OAuth initialization failed: {str(e)}"
            }

    async def complete_oauth_signin(self, sign_in_id: str) -> Dict:
        """Complete OAuth sign-in flow"""
        try:
            # Get the sign-in attempt
            signin_attempt = self.client.sign_ins.get_sign_in(sign_in_id)
            
            if signin_attempt.status == 'complete':
                # Get user details
                user = self.client.users.get_user(signin_attempt.created_user_id)
                
                # Extract user information (similar to verify_clerk_token)
                primary_email = None
                if user.email_addresses:
                    for email in user.email_addresses:
                        if email.id == user.primary_email_address_id:
                            primary_email = email.email_address
                            break
                    if not primary_email and user.email_addresses:
                        primary_email = user.email_addresses[0].email_address
                
                return {
                    'success': True,
                    'user': {
                        'id': user.id,
                        'email': primary_email,
                        'fullName': f"{user.first_name or ''} {user.last_name or ''}".strip() or primary_email or user.id
                    },
                    'sessionId': signin_attempt.created_session_id
                }
            else:
                return {
                    'success': False,
                    'error': f'OAuth not complete, status: {signin_attempt.status}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"OAuth completion failed: {str(e)}"
            }

    async def authenticate_user(self, email: str, password: str) -> Dict:
        """Authenticate user with email/password"""
        try:
            # Create sign-in attempt with email/password
            signin_attempt = self.client.sign_ins.create_sign_in(
                identifier=email,
                password=password
            )
            
            if signin_attempt.status == 'complete':
                # Get user details
                user = self.client.users.get_user(signin_attempt.created_user_id)
                
                # Extract user information
                primary_email = None
                if user.email_addresses:
                    for email_addr in user.email_addresses:
                        if email_addr.id == user.primary_email_address_id:
                            primary_email = email_addr.email_address
                            break
                    if not primary_email and user.email_addresses:
                        primary_email = user.email_addresses[0].email_address
                
                return {
                    'success': True,
                    'user': {
                        'id': user.id,
                        'email': primary_email,
                        'fullName': f"{user.first_name or ''} {user.last_name or ''}".strip() or primary_email or user.id
                    },
                    'sessionId': signin_attempt.created_session_id
                }
            else:
                return {
                    'success': False,
                    'error': f'Authentication incomplete, status: {signin_attempt.status}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Authentication failed: {str(e)}"
            }

clerk_service = ClerkService()