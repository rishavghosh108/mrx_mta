"""
Delivery Service - Business logic for outbound SMTP delivery
"""
import logging
import smtplib
import socket
import ssl
from typing import List, Tuple, Optional, Dict
from email.parser import Parser
import asyncio

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

from models.message import QueuedMessage
from services.queue_service import QueueService
import config

logger = logging.getLogger(__name__)


class DeliveryService:
    """
    Handles outbound SMTP delivery
    - MX resolution with fallback
    - IPv4/IPv6 support
    - TLS opportunistic encryption
    - Per-domain connection limits
    - Retry logic
    """
    
    def __init__(self, queue_service: QueueService):
        self.queue_service = queue_service
        self.domain_connections: Dict[str, int] = {}  # domain -> active connection count
        self.lock = asyncio.Lock()
    
    async def resolve_mx(self, domain: str) -> List[Tuple[int, str]]:
        """
        Resolve MX records for domain
        Returns list of (priority, hostname) tuples sorted by priority
        """
        if not DNS_AVAILABLE:
            logger.warning("DNS resolution unavailable, using fallback")
            return [(10, config.RELAY_HOST)] if config.RELAY_HOST else []
        
        try:
            # Run DNS query in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            answers = await loop.run_in_executor(
                None, 
                dns.resolver.resolve, 
                domain, 
                'MX'
            )
            
            mx_records = [(r.preference, str(r.exchange).rstrip('.')) for r in answers]
            mx_records.sort()  # Sort by priority (lower is higher priority)
            logger.debug(f"MX records for {domain}: {mx_records}")
            return mx_records
        
        except dns.resolver.NXDOMAIN:
            logger.warning(f"Domain {domain} does not exist")
            return []
        
        except dns.resolver.NoAnswer:
            # No MX records, try A record fallback
            if config.MX_FALLBACK_TO_A:
                logger.info(f"No MX for {domain}, trying A record fallback")
                try:
                    loop = asyncio.get_event_loop()
                    answers = await loop.run_in_executor(
                        None,
                        dns.resolver.resolve,
                        domain,
                        'A'
                    )
                    if answers:
                        return [(10, domain)]
                except:
                    pass
            return []
        
        except Exception as e:
            logger.error(f"MX resolution error for {domain}: {e}")
            # Fallback to relay host if configured
            if config.RELAY_HOST:
                return [(10, config.RELAY_HOST)]
            return []
    
    async def deliver_message(self, queued_msg: QueuedMessage) -> bool:
        """
        Attempt to deliver a queued message
        Returns True if all recipients succeeded
        """
        # Group recipients by domain
        recipients_by_domain = {}
        for recipient in queued_msg.pending_recipients():
            domain = recipient.split('@')[1]
            if domain not in recipients_by_domain:
                recipients_by_domain[domain] = []
            recipients_by_domain[domain].append(recipient)
        
        # Deliver to each domain
        all_success = True
        
        for domain, recipients in recipients_by_domain.items():
            smtp_code, smtp_message = await self.deliver_to_domain(
                queued_msg, domain, recipients
            )
            
            # Update status for these recipients
            for recipient in recipients:
                await self.queue_service.update_delivery_status(
                    queued_msg.queue_id, recipient, smtp_code, smtp_message
                )
            
            if smtp_code < 200 or smtp_code >= 300:
                all_success = False
        
        return all_success
    
    async def deliver_to_domain(self, queued_msg: QueuedMessage, 
                               domain: str, recipients: List[str]) -> Tuple[int, str]:
        """
        Deliver to all recipients in a domain
        Returns (smtp_code, smtp_message)
        """
        # Check connection limit for domain
        async with self.lock:
            active = self.domain_connections.get(domain, 0)
            if active >= config.MAX_CONNECTIONS_PER_DOMAIN:
                logger.warning(f"Connection limit reached for domain {domain}")
                return (450, "Connection limit reached for domain")
            
            self.domain_connections[domain] = active + 1
        
        try:
            # Resolve MX records
            mx_records = await self.resolve_mx(domain)
            
            if not mx_records:
                logger.error(f"No MX records found for {domain}")
                return (550, f"No MX records for {domain}")
            
            # Try each MX in order
            last_code = 450
            last_message = "All MX hosts failed"
            
            for priority, mx_host in mx_records:
                try:
                    smtp_code, smtp_message = await self.attempt_delivery(
                        mx_host, queued_msg, recipients
                    )
                    
                    if 200 <= smtp_code < 300:
                        # Success
                        return (smtp_code, smtp_message)
                    
                    # Save last error
                    last_code = smtp_code
                    last_message = smtp_message
                    
                    # If permanent error (5xx), don't try other MXes
                    if smtp_code >= 500:
                        return (smtp_code, smtp_message)
                
                except Exception as e:
                    logger.error(f"Error delivering to {mx_host}: {e}")
                    last_message = str(e)
                    continue
            
            # All MXes failed with temporary errors
            return (last_code, last_message)
        
        finally:
            async with self.lock:
                self.domain_connections[domain] -= 1
    
    async def attempt_delivery(self, mx_host: str, queued_msg: QueuedMessage, 
                              recipients: List[str]) -> Tuple[int, str]:
        """
        Attempt delivery to a specific MX host
        Returns (smtp_code, smtp_message)
        """
        logger.info(f"[{queued_msg.queue_id}] Attempting delivery to {mx_host} for {len(recipients)} recipients")
        
        # Parse message to get EmailMessage object
        parser = Parser()
        email_msg = parser.parsestr(queued_msg.message.data)
        
        # Run SMTP delivery in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        try:
            smtp_code, smtp_message = await loop.run_in_executor(
                None,
                self._smtp_send,
                mx_host,
                queued_msg.message.sender,
                recipients,
                email_msg
            )
            
            return (smtp_code, smtp_message)
        
        except Exception as e:
            logger.exception(f"[{queued_msg.queue_id}] Fatal error in delivery: {e}")
            return (451, str(e))
    
    def _smtp_send(self, mx_host: str, sender: str, recipients: List[str], 
                   email_msg) -> Tuple[int, str]:
        """
        Synchronous SMTP send (runs in thread pool)
        Returns (smtp_code, smtp_message)
        """
        try:
            # Try SMTP delivery
            with smtplib.SMTP(mx_host, 25, timeout=config.SMTP_CONNECT_TIMEOUT) as smtp:
                smtp.set_debuglevel(0)
                smtp.ehlo_or_helo_if_needed()
                
                # Try STARTTLS if available
                if smtp.has_extn('STARTTLS'):
                    try:
                        context = ssl.create_default_context()
                        context.check_hostname = False  # Some servers have mismatched certs
                        context.verify_mode = ssl.CERT_NONE  # Be permissive with remote certs
                        smtp.starttls(context=context)
                        smtp.ehlo_or_helo_if_needed()
                        logger.debug(f"TLS established with {mx_host}")
                    except Exception as e:
                        logger.warning(f"STARTTLS failed: {e}, continuing without TLS")
                
                # Send message
                smtp.send_message(
                    email_msg,
                    from_addr=sender,
                    to_addrs=recipients
                )
                
                logger.info(f"Successfully delivered to {mx_host}")
                return (250, "Message accepted for delivery")
        
        except smtplib.SMTPRecipientsRefused as e:
            # All recipients refused - permanent error
            logger.error(f"All recipients refused by {mx_host}: {e}")
            return (550, str(e))
        
        except smtplib.SMTPSenderRefused as e:
            # Sender refused - permanent error
            logger.error(f"Sender refused by {mx_host}: {e}")
            return (550, str(e))
        
        except smtplib.SMTPDataError as e:
            # Data error - could be permanent or temporary
            code = e.smtp_code
            if code and 500 <= code < 600:
                logger.error(f"SMTP data error {code}: {e}")
                return (code, str(e))
            else:
                return (451, str(e))
        
        except smtplib.SMTPResponseException as e:
            # Other SMTP errors
            code = e.smtp_code if e.smtp_code else 451
            logger.error(f"SMTP error {code}: {e}")
            return (code, str(e))
        
        except (socket.timeout, socket.error) as e:
            # Network errors - temporary
            logger.warning(f"Network error connecting to {mx_host}: {e}")
            return (450, str(e))
        
        except Exception as e:
            # Unknown error - treat as temporary
            logger.exception(f"Unexpected error delivering to {mx_host}: {e}")
            return (451, str(e))
    
    async def get_domain_connection_count(self, domain: str) -> int:
        """Get current active connection count for domain"""
        async with self.lock:
            return self.domain_connections.get(domain, 0)
