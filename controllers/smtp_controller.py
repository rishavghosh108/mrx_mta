"""
SMTP Controller - Handle SMTP protocol sessions
"""
import asyncio
import logging
import re
import ssl
import base64
from datetime import datetime
from email.utils import formatdate, make_msgid
from typing import Optional, List

from services.auth_service import AuthService
from services.queue_service import QueueService
from services.policy_service import PolicyService
from views.smtp_response_view import SMTPResponseView
import config

logger = logging.getLogger(__name__)


class SMTPState:
    """SMTP session state machine states"""
    INITIAL = 'INITIAL'
    GREETED = 'GREETED'
    AUTHENTICATED = 'AUTHENTICATED'
    MAIL = 'MAIL'
    RCPT = 'RCPT'
    DATA = 'DATA'
    QUIT = 'QUIT'


class SMTPSession:
    """
    Represents a single SMTP session
    Maintains state, envelope, and authentication info
    """
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 server_name: str, is_submission: bool = False):
        self.reader = reader
        self.writer = writer
        self.server_name = server_name
        self.is_submission = is_submission
        
        # Session state
        self.state = SMTPState.INITIAL
        self.peer_name = writer.get_extra_info('peername')
        self.peer_ip = self.peer_name[0] if self.peer_name else 'unknown'
        self.session_id = make_msgid(domain=config.DOMAIN).strip('<>')
        
        # Protocol state
        self.helo_name = None
        self.esmtp = False
        self.tls_active = False
        self.authenticated_user = None
        
        # Envelope
        self.mail_from = None
        self.rcpt_to = []
        self.message_data = None
        
        # Limits & counters
        self.error_count = 0
        self.unknown_command_count = 0
        
        # Message metadata
        self.queue_id = None
        
        logger.info(f"[{self.session_id}] New connection from {self.peer_ip}")
    
    def is_authenticated(self) -> bool:
        """Check if session is authenticated"""
        return self.authenticated_user is not None
    
    def requires_auth(self) -> bool:
        """Check if authentication is required for this session"""
        return self.is_submission and config.AUTH_REQUIRED_SUBMISSION
    
    def requires_tls(self) -> bool:
        """Check if TLS is required for this session"""
        return self.is_submission and config.TLS_REQUIRED_ON_SUBMISSION
    
    def reset_envelope(self):
        """Reset mail transaction (RSET command or after DATA)"""
        self.mail_from = None
        self.rcpt_to = []
        self.message_data = None
        if self.state in [SMTPState.MAIL, SMTPState.RCPT, SMTPState.DATA]:
            self.state = SMTPState.GREETED


class SMTPController:
    """
    SMTP Protocol Handler - RFC 5321
    Implements command parsing and response generation using MVC services
    """
    
    # Email address regex (simplified RFC 5321)
    EMAIL_REGEX = re.compile(r'^<?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>?$')
    
    def __init__(self, auth_service: AuthService, queue_service: QueueService,
                 policy_service: PolicyService):
        self.auth_service = auth_service
        self.queue_service = queue_service
        self.policy_service = policy_service
        self.view = SMTPResponseView()
    
    async def handle_session(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                            server_name: str, is_submission: bool = False):
        """Handle a complete SMTP session"""
        session = SMTPSession(reader, writer, server_name, is_submission)
        
        try:
            # Send greeting
            await self._send_reply(session, self.view.greeting(server_name))
            
            # Process commands
            while session.state != SMTPState.QUIT:
                try:
                    # Read command with timeout
                    line = await asyncio.wait_for(
                        reader.readline(),
                        timeout=config.SMTP_TIMEOUT
                    )
                    
                    if not line:
                        logger.info(f"[{session.session_id}] Client disconnected")
                        break
                    
                    await self._handle_command(session, line.decode('utf-8', errors='replace'))
                    
                except asyncio.TimeoutError:
                    await self._send_reply(session, self.view.service_not_available("Timeout"))
                    break
                except Exception as e:
                    logger.error(f"[{session.session_id}] Error handling command: {e}")
                    session.error_count += 1
                    if session.error_count >= config.SMTP_MAX_ERRORS:
                        await self._send_reply(session, self.view.service_not_available("Too many errors"))
                        break
        
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            logger.info(f"[{session.session_id}] Connection closed")
    
    async def _send_reply(self, session: SMTPSession, reply: str):
        """Send SMTP reply to client"""
        logger.debug(f"[{session.session_id}] S: {reply.strip()}")
        session.writer.write(reply.encode('utf-8'))
        await session.writer.drain()
    
    async def _handle_command(self, session: SMTPSession, line: str):
        """Parse and dispatch SMTP command"""
        line = line.rstrip('\r\n')
        logger.debug(f"[{session.session_id}] C: {line}")
        
        if not line:
            await self._send_reply(session, self.view.syntax_error("Empty command"))
            return
        
        parts = line.split(None, 1)
        command = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ''
        
        # Command dispatch
        handlers = {
            'HELO': self._handle_HELO,
            'EHLO': self._handle_EHLO,
            'STARTTLS': self._handle_STARTTLS,
            'AUTH': self._handle_AUTH,
            'MAIL': self._handle_MAIL,
            'RCPT': self._handle_RCPT,
            'DATA': self._handle_DATA,
            'RSET': self._handle_RSET,
            'NOOP': self._handle_NOOP,
            'QUIT': self._handle_QUIT,
            'VRFY': self._handle_VRFY,
            'EXPN': self._handle_EXPN,
            'HELP': self._handle_HELP,
        }
        
        handler = handlers.get(command)
        if handler:
            await handler(session, args)
        else:
            session.unknown_command_count += 1
            await self._send_reply(session, self.view.not_implemented(command))
            
            if session.unknown_command_count >= config.SMTP_MAX_UNKNOWN_COMMANDS:
                await self._send_reply(session, self.view.service_not_available("Too many unknown commands"))
                session.state = SMTPState.QUIT
    
    async def _handle_HELO(self, session: SMTPSession, args: str):
        """Handle HELO command (RFC 5321 Section 4.1.1.1)"""
        if not args:
            await self._send_reply(session, self.view.syntax_error_param("HELO requires domain address"))
            return
        
        session.helo_name = args
        session.esmtp = False
        session.state = SMTPState.GREETED
        session.reset_envelope()
        
        await self._send_reply(session, self.view.ok(f"{session.server_name} Hello {session.peer_ip}"))
    
    async def _handle_EHLO(self, session: SMTPSession, args: str):
        """Handle EHLO command - Extended SMTP (RFC 5321 Section 4.1.1.1)"""
        if not args:
            await self._send_reply(session, self.view.syntax_error_param("EHLO requires domain address"))
            return
        
        session.helo_name = args
        session.esmtp = True
        session.state = SMTPState.GREETED
        session.reset_envelope()
        
        # Build extension list
        extensions = []
        extensions.append(f"SIZE {config.SMTP_MAX_MESSAGE_SIZE}")
        extensions.append("8BITMIME")
        extensions.append("PIPELINING")
        extensions.append("ENHANCEDSTATUSCODES")
        extensions.append("DSN")
        
        # STARTTLS only if not already in TLS and we have cert
        if not session.tls_active and config.TLS_CERT_FILE:
            extensions.append("STARTTLS")
        
        # AUTH only after TLS or if not required
        if session.tls_active or not session.requires_tls():
            if config.AUTH_MECHANISMS:
                auth_mechs = ' '.join(config.AUTH_MECHANISMS)
                extensions.append(f"AUTH {auth_mechs}")
        
        await self._send_reply(session, self.view.ehlo(session.server_name, session.peer_ip, extensions))
    
    async def _handle_STARTTLS(self, session: SMTPSession, args: str):
        """Handle STARTTLS command (RFC 3207)"""
        if session.tls_active:
            await self._send_reply(session, self.view.bad_sequence("Already in TLS mode"))
            return
        
        if args:
            await self._send_reply(session, self.view.syntax_error_param("STARTTLS does not accept parameters"))
            return
        
        await self._send_reply(session, self.view.starttls_ready())
        
        # Upgrade connection to TLS
        try:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(config.TLS_CERT_FILE, config.TLS_KEY_FILE)
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            ssl_context.set_ciphers(config.TLS_CIPHERS)
            
            # Get the transport and upgrade
            transport = session.writer.transport
            protocol = transport.get_protocol()
            
            await asyncio.get_event_loop().start_tls(
                transport, protocol, ssl_context,
                server_side=True
            )
            
            session.tls_active = True
            session.state = SMTPState.INITIAL  # Reset to require new EHLO
            logger.info(f"[{session.session_id}] TLS negotiation successful")
            
        except Exception as e:
            logger.error(f"[{session.session_id}] TLS negotiation failed: {e}")
            await self._send_reply(session, self.view.local_error("TLS negotiation failed"))
    
    async def _handle_AUTH(self, session: SMTPSession, args: str):
        """Handle AUTH command (RFC 4954)"""
        if not session.esmtp:
            await self._send_reply(session, self.view.bad_sequence("Use EHLO first"))
            return
        
        if session.is_authenticated():
            await self._send_reply(session, self.view.bad_sequence("Already authenticated"))
            return
        
        if session.requires_tls() and not session.tls_active:
            await self._send_reply(session, self.view.syntax_error("Must issue STARTTLS first"))
            return
        
        parts = args.split(None, 1)
        if not parts:
            await self._send_reply(session, self.view.syntax_error_param("AUTH mechanism required"))
            return
        
        mechanism = parts[0].upper()
        initial_response = parts[1] if len(parts) > 1 else None
        
        if mechanism == 'PLAIN':
            await self._handle_AUTH_PLAIN(session, initial_response)
        elif mechanism == 'LOGIN':
            await self._handle_AUTH_LOGIN(session, initial_response)
        else:
            await self._send_reply(session, 
                self.view.format_reply(504, f"AUTH mechanism {mechanism} not supported"))
    
    async def _handle_AUTH_PLAIN(self, session: SMTPSession, initial_response: Optional[str]):
        """Handle AUTH PLAIN mechanism"""
        if not initial_response:
            # Request credentials
            await self._send_reply(session, self.view.auth_continue())
            
            response = await session.reader.readline()
            initial_response = response.decode('utf-8').strip()
        
        try:
            # Decode: \0username\0password
            decoded = base64.b64decode(initial_response).decode('utf-8')
            parts = decoded.split('\0')
            if len(parts) == 3:
                username = parts[1]
                password = parts[2]
            else:
                raise ValueError("Invalid PLAIN format")
            
            # Authenticate using service
            user = await self.auth_service.authenticate(username, password, session.peer_ip)
            
            if user:
                session.authenticated_user = username
                session.state = SMTPState.AUTHENTICATED
                await self._send_reply(session, self.view.auth_success())
                logger.info(f"[{session.session_id}] User {username} authenticated")
            else:
                await self._send_reply(session, self.view.auth_failed())
                logger.warning(f"[{session.session_id}] Authentication failed for {username}")
        
        except Exception as e:
            logger.error(f"[{session.session_id}] AUTH PLAIN error: {e}")
            await self._send_reply(session, self.view.auth_failed())
    
    async def _handle_AUTH_LOGIN(self, session: SMTPSession, initial_response: Optional[str]):
        """Handle AUTH LOGIN mechanism"""
        try:
            # Request username
            session.writer.write(b'334 VXNlcm5hbWU6\r\n')  # "Username:" in base64
            await session.writer.drain()
            
            username_line = await session.reader.readline()
            username = base64.b64decode(username_line.strip()).decode('utf-8')
            
            # Request password
            session.writer.write(b'334 UGFzc3dvcmQ6\r\n')  # "Password:" in base64
            await session.writer.drain()
            
            password_line = await session.reader.readline()
            password = base64.b64decode(password_line.strip()).decode('utf-8')
            
            # Authenticate using service
            user = await self.auth_service.authenticate(username, password, session.peer_ip)
            
            if user:
                session.authenticated_user = username
                session.state = SMTPState.AUTHENTICATED
                await self._send_reply(session, self.view.auth_success())
                logger.info(f"[{session.session_id}] User {username} authenticated")
            else:
                await self._send_reply(session, self.view.auth_failed())
                logger.warning(f"[{session.session_id}] Authentication failed for {username}")
        
        except Exception as e:
            logger.error(f"[{session.session_id}] AUTH LOGIN error: {e}")
            await self._send_reply(session, self.view.auth_failed())
    
    async def _handle_MAIL(self, session: SMTPSession, args: str):
        """Handle MAIL FROM command (RFC 5321 Section 4.1.1.2)"""
        if session.state not in [SMTPState.GREETED, SMTPState.AUTHENTICATED]:
            await self._send_reply(session, self.view.bad_sequence("Use HELO/EHLO first"))
            return
        
        if session.requires_auth() and not session.is_authenticated():
            await self._send_reply(session, self.view.auth_required())
            return
        
        if not args.upper().startswith('FROM:'):
            await self._send_reply(session, self.view.syntax_error_param("Syntax: MAIL FROM:<address>"))
            return
        
        # Parse address
        address_part = args[5:].strip()
        match = self.EMAIL_REGEX.match(address_part)
        
        if not match and address_part != '<>':  # Allow null sender
            await self._send_reply(session, self.view.syntax_error_param("Invalid sender address"))
            return
        
        sender = match.group(1) if match else ''
        
        # Policy checks
        sender_domain = sender.split('@')[1] if sender and '@' in sender else None
        
        # Check blacklist
        if await self.policy_service.check_blacklist(ip=session.peer_ip, domain=sender_domain, email=sender):
            await self._send_reply(session, self.view.policy_rejected("Sender blacklisted"))
            return
        
        # Check rate limit
        if session.authenticated_user:
            user = await self.auth_service.get_user(session.authenticated_user)
            if user and not await self.policy_service.check_user_rate_limit(
                session.authenticated_user, user.rate_limit
            ):
                await self._send_reply(session, self.view.rate_limited())
                return
        else:
            if not await self.policy_service.check_ip_rate_limit(session.peer_ip):
                await self._send_reply(session, self.view.rate_limited())
                return
        
        session.mail_from = sender
        session.state = SMTPState.MAIL
        await self._send_reply(session, self.view.sender_ok(sender))
    
    async def _handle_RCPT(self, session: SMTPSession, args: str):
        """Handle RCPT TO command (RFC 5321 Section 4.1.1.3)"""
        if session.state not in [SMTPState.MAIL, SMTPState.RCPT]:
            await self._send_reply(session, self.view.bad_sequence("Use MAIL FROM first"))
            return
        
        if not args.upper().startswith('TO:'):
            await self._send_reply(session, self.view.syntax_error_param("Syntax: RCPT TO:<address>"))
            return
        
        # Check recipient limit
        if len(session.rcpt_to) >= config.SMTP_MAX_RECIPIENTS:
            await self._send_reply(session, self.view.exceeded_storage("Too many recipients"))
            return
        
        # Parse address
        address_part = args[3:].strip()
        match = self.EMAIL_REGEX.match(address_part)
        
        if not match:
            await self._send_reply(session, self.view.syntax_error_param("Invalid recipient address"))
            return
        
        recipient = match.group(1)
        recipient_domain = recipient.split('@')[1] if '@' in recipient else None
        
        # Policy checks - blacklist
        if await self.policy_service.check_blacklist(domain=recipient_domain, email=recipient):
            await self._send_reply(session, self.view.policy_rejected("Recipient blacklisted"))
            return
        
        # Greylisting (if enabled and not authenticated)
        if config.GREYLIST_ENABLED and not session.is_authenticated():
            passed, reason = await self.policy_service.check_greylist(
                session.mail_from, recipient, session.peer_ip
            )
            if not passed:
                await self._send_reply(session, self.view.greylisted())
                return
        
        session.rcpt_to.append(recipient)
        session.state = SMTPState.RCPT
        await self._send_reply(session, self.view.recipient_ok(recipient))
    
    async def _handle_DATA(self, session: SMTPSession, args: str):
        """Handle DATA command (RFC 5321 Section 4.1.1.4)"""
        if session.state != SMTPState.RCPT:
            await self._send_reply(session, self.view.bad_sequence("Use RCPT TO first"))
            return
        
        if args:
            await self._send_reply(session, self.view.syntax_error_param("DATA does not accept parameters"))
            return
        
        await self._send_reply(session, self.view.start_data())
        
        # Read message data until .<CRLF>
        message_lines = []
        total_size = 0
        
        while True:
            line = await session.reader.readline()
            if not line:
                await self._send_reply(session, self.view.local_error("Connection lost during DATA"))
                return
            
            line_str = line.decode('utf-8', errors='replace')
            
            # Check for end of data
            if line_str.rstrip('\r\n') == '.':
                break
            
            # Remove transparency (leading dot)
            if line_str.startswith('..'):
                line_str = line_str[1:]
            
            message_lines.append(line_str)
            total_size += len(line_str)
            
            # Check size limit
            if total_size > config.SMTP_MAX_MESSAGE_SIZE:
                await self._send_reply(session, self.view.exceeded_storage("Message size exceeds limit"))
                return
        
        session.message_data = ''.join(message_lines)
        
        # Add Received header
        received_header = self._generate_received_header(session)
        session.message_data = received_header + session.message_data
        
        try:
            # Queue the message using service
            queued_msg = await self.queue_service.enqueue_message(
                sender=session.mail_from,
                recipients=session.rcpt_to,
                message_data=session.message_data,
                session_info={
                    'peer_ip': session.peer_ip,
                    'helo_name': session.helo_name,
                    'authenticated_user': session.authenticated_user,
                    'tls_active': session.tls_active,
                }
            )
            
            session.queue_id = queued_msg.queue_id
            await self._send_reply(session, self.view.message_accepted(queued_msg.queue_id))
            logger.info(f"[{session.session_id}] Message queued as {queued_msg.queue_id}")
            
            # Print incoming mail to console
            print("\n" + "="*70)
            print("📧 INCOMING MAIL RECEIVED")
            print("="*70)
            print(f"Queue ID    : {queued_msg.queue_id}")
            print(f"From        : {session.mail_from}")
            print(f"To          : {', '.join(session.rcpt_to)}")
            print(f"Peer IP     : {session.peer_ip}")
            print(f"Auth User   : {session.authenticated_user or 'None'}")
            print(f"TLS Active  : {session.tls_active}")
            print(f"Size        : {len(session.message_data)} bytes")
            print(f"Time        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-"*70)
            # Print message preview (first 500 chars)
            message_preview = session.message_data[:500]
            if len(session.message_data) > 500:
                message_preview += "\n... (message truncated for display)"
            print("Message Preview:")
            print(message_preview)
            print("="*70 + "\n")
            
        except Exception as e:
            logger.error(f"[{session.session_id}] Failed to queue message: {e}")
            await self._send_reply(session, self.view.local_error("Failed to queue message"))
        
        # Reset for next transaction
        session.reset_envelope()
    
    def _generate_received_header(self, session: SMTPSession) -> str:
        """Generate RFC 5321 compliant Received header"""
        from_part = f"from {session.helo_name} ({session.peer_ip})"
        by_part = f"by {session.server_name}"
        
        with_part = "with ESMTPS" if session.tls_active else "with ESMTP"
        if session.authenticated_user:
            with_part += "A"  # Authenticated
        
        id_part = f"id {session.queue_id or 'unknown'}"
        for_part = f"for <{session.rcpt_to[0]}>" if len(session.rcpt_to) == 1 else ""
        timestamp = formatdate(localtime=True)
        
        return f"Received: {from_part}\r\n\t{by_part} {with_part}\r\n\t{id_part} {for_part};\r\n\t{timestamp}\r\n"
    
    async def _handle_RSET(self, session: SMTPSession, args: str):
        """Handle RSET command (RFC 5321 Section 4.1.1.5)"""
        session.reset_envelope()
        await self._send_reply(session, self.view.reset_ok())
    
    async def _handle_NOOP(self, session: SMTPSession, args: str):
        """Handle NOOP command (RFC 5321 Section 4.1.1.9)"""
        await self._send_reply(session, self.view.noop_ok())
    
    async def _handle_QUIT(self, session: SMTPSession, args: str):
        """Handle QUIT command (RFC 5321 Section 4.1.1.10)"""
        await self._send_reply(session, self.view.closing(session.server_name))
        session.state = SMTPState.QUIT
    
    async def _handle_VRFY(self, session: SMTPSession, args: str):
        """Handle VRFY command - disabled for security (RFC 5321 Section 3.5.3)"""
        await self._send_reply(session, self.view.cannot_vrfy())
    
    async def _handle_EXPN(self, session: SMTPSession, args: str):
        """Handle EXPN command - disabled for security"""
        await self._send_reply(session, self.view.cannot_vrfy())
    
    async def _handle_HELP(self, session: SMTPSession, args: str):
        """Handle HELP command"""
        await self._send_reply(session, self.view.help())
