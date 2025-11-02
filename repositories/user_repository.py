"""
User Repository - Handles user data persistence
"""
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict

from models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    """
    Repository for User entities
    Implements data access abstraction for users
    """
    
    def __init__(self, storage_file: str):
        self.storage_file = storage_file
        self.lock = asyncio.Lock()
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Ensure storage file exists"""
        storage_path = Path(self.storage_file)
        if not storage_path.exists():
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            storage_path.write_text(json.dumps({}, indent=2))
    
    async def find_by_username(self, username: str) -> Optional[User]:
        """Find user by username"""
        async with self.lock:
            users_data = self._load_all()
            if username in users_data:
                return User.from_dict(users_data[username])
            return None
    
    async def find_all(self) -> List[User]:
        """Get all users"""
        async with self.lock:
            users_data = self._load_all()
            return [
                User.from_dict(user_data)
                for user_data in users_data.values()
            ]
    
    async def save(self, user: User) -> bool:
        """Save or update user"""
        async with self.lock:
            try:
                users_data = self._load_all()
                users_data[user.username] = user.to_dict_with_hash()
                self._save_all(users_data)
                logger.info(f"Saved user: {user.username}")
                return True
            except Exception as e:
                logger.error(f"Failed to save user {user.username}: {e}")
                return False
    
    async def delete(self, username: str) -> bool:
        """Delete user"""
        async with self.lock:
            try:
                users_data = self._load_all()
                if username in users_data:
                    del users_data[username]
                    self._save_all(users_data)
                    logger.info(f"Deleted user: {username}")
                    return True
                return False
            except Exception as e:
                logger.error(f"Failed to delete user {username}: {e}")
                return False
    
    async def exists(self, username: str) -> bool:
        """Check if user exists"""
        async with self.lock:
            users_data = self._load_all()
            return username in users_data
    
    async def count(self) -> int:
        """Count total users"""
        async with self.lock:
            users_data = self._load_all()
            return len(users_data)
    
    def _load_all(self) -> Dict:
        """Load all users from storage (synchronous)"""
        try:
            storage_path = Path(self.storage_file)
            if storage_path.exists():
                return json.loads(storage_path.read_text())
            return {}
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            return {}
    
    def _save_all(self, users_data: Dict):
        """Save all users to storage (synchronous)"""
        storage_path = Path(self.storage_file)
        storage_path.write_text(json.dumps(users_data, indent=2))
    
    async def create_default_user(self, username: str, password: str) -> User:
        """Create default user if not exists"""
        user = await self.find_by_username(username)
        if user is None:
            user = User.create(username, password)
            await self.save(user)
            logger.info(f"Created default user: {username}")
        return user
