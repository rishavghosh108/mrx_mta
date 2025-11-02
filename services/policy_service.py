"""
Policy Service - Business logic for policy enforcement
"""
import logging
import time
from typing import Optional
import asyncio

from models.policy import RateLimit, GreylistEntry, PolicyRule
from repositories.policy_repository import PolicyRepository
import config

logger = logging.getLogger(__name__)


class PolicyService:
    """
    Policy enforcement business logic
    Handles rate limiting, blacklisting, greylisting, and SPF checking
    """
    
    def __init__(self, policy_repository: PolicyRepository):
        self.policy_repo = policy_repository
        self.lock = asyncio.Lock()
    
    # Blacklist/Whitelist
    async def check_blacklist(self, ip: str = None, domain: str = None, email: str = None) -> bool:
        """Check if IP, domain, or email is blacklisted"""
        targets = [t for t in [ip, domain, email] if t]
        
        for target in targets:
            if await self.policy_repo.is_blacklisted(target):
                logger.warning(f"Blacklisted: {target}")
                return True
        
        return False
    
    async def check_whitelist(self, ip: str = None, domain: str = None, email: str = None) -> bool:
        """Check if IP, domain, or email is whitelisted"""
        targets = [t for t in [ip, domain, email] if t]
        
        for target in targets:
            if await self.policy_repo.is_whitelisted(target):
                logger.info(f"Whitelisted: {target}")
                return True
        
        return False
    
    async def add_to_blacklist(self, target: str, reason: str = None) -> PolicyRule:
        """Add target to blacklist"""
        return await self.policy_repo.add_blacklist(target, reason)
    
    async def remove_from_blacklist(self, target: str) -> bool:
        """Remove from blacklist"""
        return await self.policy_repo.remove_blacklist(target)
    
    # Rate Limiting
    async def check_rate_limit(self, identifier: str, limit_type: str, 
                              capacity: int, refill_rate: float) -> bool:
        """
        Check rate limit using token bucket algorithm
        Returns True if allowed, False if rate limited
        """
        async with self.lock:
            # Get or create rate limit
            rate_limit = await self.policy_repo.get_rate_limit(identifier, limit_type)
            
            if rate_limit is None:
                # Create new rate limit
                rate_limit = RateLimit(
                    identifier=identifier,
                    limit_type=limit_type,
                    capacity=capacity,
                    tokens=float(capacity),
                    refill_rate=refill_rate
                )
            
            # Check if allowed
            allowed = rate_limit.consume(1)
            
            # Save updated state
            await self.policy_repo.save_rate_limit(rate_limit)
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {limit_type}:{identifier}")
            
            return allowed
    
    async def check_ip_rate_limit(self, ip: str) -> bool:
        """Check per-IP rate limit"""
        return await self.check_rate_limit(
            ip, 'ip',
            config.RATE_LIMIT_PER_IP,
            config.RATE_LIMIT_PER_IP / 3600  # Refill over 1 hour
        )
    
    async def check_user_rate_limit(self, username: str, user_limit: int = None) -> bool:
        """Check per-user rate limit"""
        limit = user_limit or config.RATE_LIMIT_PER_USER
        return await self.check_rate_limit(
            username, 'user',
            limit,
            limit / 3600
        )
    
    async def check_domain_rate_limit(self, domain: str) -> bool:
        """Check per-domain rate limit"""
        return await self.check_rate_limit(
            domain, 'domain',
            config.RATE_LIMIT_PER_DOMAIN,
            config.RATE_LIMIT_PER_DOMAIN / 3600
        )
    
    # Greylisting
    async def check_greylist(self, sender: str, recipient: str, ip: str) -> tuple[bool, str]:
        """
        Check greylisting
        Returns (should_accept, reason)
        """
        triplet = f"{sender}:{recipient}:{ip}"
        entry = await self.policy_repo.get_greylist_entry(triplet)
        
        if entry is None:
            # First time seeing this triplet - defer
            entry = GreylistEntry(triplet=triplet)
            await self.policy_repo.save_greylist_entry(entry)
            logger.info(f"Greylisting (first seen): {triplet}")
            return False, "Greylisted - try again later"
        
        # Update entry
        entry.update()
        
        # Check if should defer
        if entry.should_defer(config.GREYLIST_MIN_DELAY, config.GREYLIST_MAX_AGE):
            await self.policy_repo.save_greylist_entry(entry)
            return False, "Greylisted - too soon or too old"
        
        # Passed greylisting
        entry.mark_passed()
        await self.policy_repo.save_greylist_entry(entry)
        logger.info(f"Passed greylisting: {triplet}")
        return True, "Greylist passed"
    
    async def get_rate_limit_stats(self) -> dict:
        """Get rate limiting statistics"""
        limits = await self.policy_repo.get_all_rate_limits()
        
        stats = {
            'total_limits': len(limits),
            'by_type': {},
            'top_limited': []
        }
        
        for limit in limits:
            limit_type = limit.limit_type
            if limit_type not in stats['by_type']:
                stats['by_type'][limit_type] = {
                    'count': 0,
                    'total_requests': 0,
                    'rejected_requests': 0
                }
            
            stats['by_type'][limit_type]['count'] += 1
            stats['by_type'][limit_type]['total_requests'] += limit.total_requests
            stats['by_type'][limit_type]['rejected_requests'] += limit.rejected_requests
        
        # Sort by rejection rate
        sorted_limits = sorted(limits, key=lambda x: x.rejected_requests, reverse=True)
        stats['top_limited'] = [
            {
                'identifier': limit.identifier,
                'type': limit.limit_type,
                'rejected': limit.rejected_requests,
                'total': limit.total_requests
            }
            for limit in sorted_limits[:10]
        ]
        
        return stats
    
    async def cleanup(self):
        """Cleanup old entries"""
        await self.policy_repo.cleanup_rate_limits()
        await self.policy_repo.cleanup_greylist()
        logger.info("Cleaned up old policy entries")
