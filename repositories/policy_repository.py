"""
Policy Repository - Handles policy data persistence
"""
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional
import time

from models.policy import PolicyRule, RateLimit, GreylistEntry

logger = logging.getLogger(__name__)


class PolicyRepository:
    """
    Repository for policy-related entities
    Stores blacklists, whitelists, rate limits, and greylisting data
    """
    
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.blacklist_file = self.storage_dir / "blacklist.json"
        self.whitelist_file = self.storage_dir / "whitelist.json"
        self.rate_limits_file = self.storage_dir / "rate_limits.json"
        self.greylist_file = self.storage_dir / "greylist.json"
        self.lock = asyncio.Lock()
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Ensure storage directory and files exist"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        for file in [self.blacklist_file, self.whitelist_file, 
                     self.rate_limits_file, self.greylist_file]:
            if not file.exists():
                file.write_text(json.dumps({}, indent=2))
    
    # Blacklist/Whitelist methods
    async def add_blacklist(self, target: str, reason: str = None) -> PolicyRule:
        """Add target to blacklist"""
        async with self.lock:
            rules = self._load_json(self.blacklist_file)
            
            rule = PolicyRule(
                rule_id=f"bl_{int(time.time())}_{target}",
                rule_type='blacklist',
                target=target,
                action='reject',
                reason=reason
            )
            
            rules[target] = rule.to_dict()
            self._save_json(self.blacklist_file, rules)
            logger.info(f"Added to blacklist: {target}")
            return rule
    
    async def remove_blacklist(self, target: str) -> bool:
        """Remove target from blacklist"""
        async with self.lock:
            rules = self._load_json(self.blacklist_file)
            if target in rules:
                del rules[target]
                self._save_json(self.blacklist_file, rules)
                logger.info(f"Removed from blacklist: {target}")
                return True
            return False
    
    async def is_blacklisted(self, target: str) -> bool:
        """Check if target is blacklisted"""
        async with self.lock:
            rules = self._load_json(self.blacklist_file)
            return target in rules
    
    async def get_blacklist(self) -> List[PolicyRule]:
        """Get all blacklist rules"""
        async with self.lock:
            rules = self._load_json(self.blacklist_file)
            return [PolicyRule.from_dict(rule) for rule in rules.values()]
    
    async def add_whitelist(self, target: str, reason: str = None) -> PolicyRule:
        """Add target to whitelist"""
        async with self.lock:
            rules = self._load_json(self.whitelist_file)
            
            rule = PolicyRule(
                rule_id=f"wl_{int(time.time())}_{target}",
                rule_type='whitelist',
                target=target,
                action='accept',
                reason=reason
            )
            
            rules[target] = rule.to_dict()
            self._save_json(self.whitelist_file, rules)
            logger.info(f"Added to whitelist: {target}")
            return rule
    
    async def is_whitelisted(self, target: str) -> bool:
        """Check if target is whitelisted"""
        async with self.lock:
            rules = self._load_json(self.whitelist_file)
            return target in rules
    
    # Rate limit methods
    async def get_rate_limit(self, identifier: str, limit_type: str) -> Optional[RateLimit]:
        """Get rate limit for identifier"""
        async with self.lock:
            limits = self._load_json(self.rate_limits_file)
            key = f"{limit_type}:{identifier}"
            
            if key in limits:
                data = limits[key]
                return RateLimit(**data)
            return None
    
    async def save_rate_limit(self, rate_limit: RateLimit) -> bool:
        """Save rate limit state"""
        async with self.lock:
            try:
                limits = self._load_json(self.rate_limits_file)
                key = f"{rate_limit.limit_type}:{rate_limit.identifier}"
                limits[key] = rate_limit.to_dict()
                self._save_json(self.rate_limits_file, limits)
                return True
            except Exception as e:
                logger.error(f"Failed to save rate limit: {e}")
                return False
    
    async def get_all_rate_limits(self) -> List[RateLimit]:
        """Get all rate limits"""
        async with self.lock:
            limits = self._load_json(self.rate_limits_file)
            return [RateLimit(**data) for data in limits.values()]
    
    async def cleanup_rate_limits(self, max_age: int = 3600):
        """Remove old rate limit entries"""
        async with self.lock:
            limits = self._load_json(self.rate_limits_file)
            now = time.time()
            
            # Remove entries not accessed recently
            cleaned = {
                key: data for key, data in limits.items()
                if (now - data.get('last_refill', 0)) < max_age
            }
            
            if len(cleaned) < len(limits):
                self._save_json(self.rate_limits_file, cleaned)
                logger.info(f"Cleaned {len(limits) - len(cleaned)} old rate limit entries")
    
    # Greylist methods
    async def get_greylist_entry(self, triplet: str) -> Optional[GreylistEntry]:
        """Get greylist entry"""
        async with self.lock:
            entries = self._load_json(self.greylist_file)
            if triplet in entries:
                return GreylistEntry.from_dict(entries[triplet])
            return None
    
    async def save_greylist_entry(self, entry: GreylistEntry) -> bool:
        """Save greylist entry"""
        async with self.lock:
            try:
                entries = self._load_json(self.greylist_file)
                entries[entry.triplet] = entry.to_dict()
                self._save_json(self.greylist_file, entries)
                return True
            except Exception as e:
                logger.error(f"Failed to save greylist entry: {e}")
                return False
    
    async def cleanup_greylist(self, max_age: int = 86400):
        """Remove old greylist entries"""
        async with self.lock:
            entries = self._load_json(self.greylist_file)
            now = time.time()
            
            # Remove old entries
            cleaned = {
                triplet: data for triplet, data in entries.items()
                if (now - data.get('last_seen', 0)) < max_age
            }
            
            if len(cleaned) < len(entries):
                self._save_json(self.greylist_file, cleaned)
                logger.info(f"Cleaned {len(entries) - len(cleaned)} old greylist entries")
    
    # Helper methods
    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON file"""
        try:
            if file_path.exists():
                return json.loads(file_path.read_text())
            return {}
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return {}
    
    def _save_json(self, file_path: Path, data: Dict):
        """Save JSON file"""
        file_path.write_text(json.dumps(data, indent=2))
