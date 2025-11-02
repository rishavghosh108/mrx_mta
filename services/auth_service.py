"""
Authentication Service - Business logic for authentication
"""
import logging
import time
from typing import Optional, Dict, List
import asyncio

from models.user import User
from repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication business logic
    Handles user authentication, lockouts, and session management
    """
    
    def __init__(self, user_repository: UserRepository, 
                 max_attempts: int = 5, lockout_duration: int = 300):
        self.user_repo = user_repository
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration
        
        # Track failed attempts per IP
        self.failed_attempts: Dict[str, List[float]] = {}
        self.locked_ips: Dict[str, float] = {}
        self.lock = asyncio.Lock()
    
    async def authenticate(self, username: str, password: str, peer_ip: str) -> Optional[User]:
        """
        Authenticate user
        Returns User object if successful, None otherwise
        """
        async with self.lock:
            # Check if IP is locked out
            if self._is_locked(peer_ip):
                logger.warning(f"Authentication attempt from locked IP: {peer_ip}")
                return None
            
            # Find user
            user = await self.user_repo.find_by_username(username)
            
            if user is None:
                await self._record_failure(peer_ip)
                logger.warning(f"Authentication failed: user not found - {username}")
                return None
            
            # Check if user is enabled
            if not user.enabled:
                logger.warning(f"Authentication attempt for disabled user: {username}")
                return None
            
            # Verify password
            if not user.verify_password(password):
                await self._record_failure(peer_ip)
                logger.warning(f"Authentication failed: invalid password - {username}")
                return None
            
            # Success - record login and clear failures
            user.record_login()
            await self.user_repo.save(user)
            self._clear_failures(peer_ip)
            
            logger.info(f"User authenticated: {username} from {peer_ip}")
            return user
    
    async def create_user(self, username: str, password: str, **kwargs) -> User:
        """Create new user"""
        user = User.create(username, password, **kwargs)
        await self.user_repo.save(user)
        logger.info(f"Created user: {username}")
        return user
    
    async def update_user(self, username: str, **updates) -> bool:
        """Update user properties"""
        user = await self.user_repo.find_by_username(username)
        if user is None:
            return False
        
        # Update allowed fields
        for key, value in updates.items():
            if hasattr(user, key) and key != 'password_hash':
                setattr(user, key, value)
        
        await self.user_repo.save(user)
        logger.info(f"Updated user: {username}")
        return True
    
    async def change_password(self, username: str, new_password: str) -> bool:
        """Change user password"""
        user = await self.user_repo.find_by_username(username)
        if user is None:
            return False
        
        user.password_hash = User.hash_password(new_password)
        await self.user_repo.save(user)
        logger.info(f"Changed password for user: {username}")
        return True
    
    async def delete_user(self, username: str) -> bool:
        """Delete user"""
        result = await self.user_repo.delete(username)
        if result:
            logger.info(f"Deleted user: {username}")
        return result
    
    async def list_users(self) -> List[User]:
        """List all users"""
        return await self.user_repo.find_all()
    
    async def get_user(self, username: str) -> Optional[User]:
        """Get user by username"""
        return await self.user_repo.find_by_username(username)
    
    def _is_locked(self, ip: str) -> bool:
        """Check if IP is locked out"""
        if ip not in self.locked_ips:
            return False
        
        if time.time() < self.locked_ips[ip]:
            return True
        
        # Lockout expired
        del self.locked_ips[ip]
        self.failed_attempts[ip] = []
        return False
    
    async def _record_failure(self, ip: str):
        """Record failed authentication attempt"""
        now = time.time()
        
        if ip not in self.failed_attempts:
            self.failed_attempts[ip] = []
        
        # Add current failure
        self.failed_attempts[ip].append(now)
        
        # Remove old attempts (older than lockout duration)
        self.failed_attempts[ip] = [
            timestamp for timestamp in self.failed_attempts[ip]
            if now - timestamp < self.lockout_duration
        ]
        
        # Check if should lock
        if len(self.failed_attempts[ip]) >= self.max_attempts:
            self.locked_ips[ip] = now + self.lockout_duration
            logger.warning(f"Locked IP due to {self.max_attempts} failed attempts: {ip}")
    
    def _clear_failures(self, ip: str):
        """Clear failed attempts for IP"""
        if ip in self.failed_attempts:
            del self.failed_attempts[ip]
        if ip in self.locked_ips:
            del self.locked_ips[ip]
    
    async def validate_rate_limit(self, user: User) -> bool:
        """
        Validate if user is within rate limit
        This is a placeholder - actual rate limiting in PolicyService
        """
        # TODO: Integrate with PolicyService for actual rate limiting
        return True
