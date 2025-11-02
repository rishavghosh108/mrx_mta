"""
SMTP Response View - Format SMTP protocol responses
"""
from typing import List, Optional
from datetime import datetime


class SMTPResponseView:
    """
    Format SMTP responses according to RFC 5321
    Includes enhanced status codes (RFC 3463)
    """
    
    # SMTP Reply codes (RFC 5321 Section 4.2)
    CODE_SYSTEM_STATUS = 211
    CODE_HELP = 214
    CODE_READY = 220
    CODE_CLOSING = 221
    CODE_AUTH_SUCCESS = 235
    CODE_OK = 250
    CODE_USER_NOT_LOCAL = 251
    CODE_CANNOT_VRFY = 252
    CODE_AUTH_CONTINUE = 334
    CODE_START_MAIL = 354
    
    CODE_SERVICE_NOT_AVAILABLE = 421
    CODE_MAILBOX_UNAVAILABLE = 450
    CODE_LOCAL_ERROR = 451
    CODE_INSUFFICIENT_STORAGE = 452
    
    CODE_SYNTAX_ERROR = 500
    CODE_SYNTAX_ERROR_PARAM = 501
    CODE_NOT_IMPLEMENTED = 502
    CODE_BAD_SEQUENCE = 503
    CODE_PARAM_NOT_IMPLEMENTED = 504
    CODE_AUTH_REQUIRED = 530
    CODE_AUTH_FAILED = 535
    CODE_MAILBOX_NOT_FOUND = 550
    CODE_USER_NOT_LOCAL_TRY_FORWARD = 551
    CODE_EXCEEDED_STORAGE = 552
    CODE_MAILBOX_NAME_INVALID = 553
    CODE_TRANSACTION_FAILED = 554
    
    # Enhanced status codes (RFC 3463)
    ENHANCED_CODES = {
        220: '2.0.0',
        221: '2.0.0',
        235: '2.7.0',
        250: '2.0.0',
        251: '2.1.5',
        252: '2.5.3',
        354: '2.0.0',
        421: '4.3.0',
        450: '4.2.0',
        451: '4.3.0',
        452: '4.2.2',
        500: '5.5.2',
        501: '5.5.4',
        502: '5.5.1',
        503: '5.5.1',
        504: '5.5.4',
        530: '5.7.0',
        535: '5.7.8',
        550: '5.1.1',
        551: '5.1.6',
        552: '5.2.2',
        553: '5.1.3',
        554: '5.5.0',
    }
    
    @classmethod
    def format_reply(cls, code: int, message: str, multiline: Optional[List[str]] = None) -> str:
        """
        Format SMTP reply with optional enhanced status codes
        
        Args:
            code: SMTP reply code
            message: Reply message
            multiline: Optional list of additional lines
            
        Returns:
            Formatted SMTP reply string ending with CRLF
        """
        enhanced = cls.ENHANCED_CODES.get(code, '')
        if enhanced:
            enhanced = f"{enhanced} "
        
        if multiline:
            lines = [f"{code}-{enhanced}{line}" for line in multiline]
            lines.append(f"{code} {enhanced}{message}")
            return '\r\n'.join(lines) + '\r\n'
        else:
            return f"{code} {enhanced}{message}\r\n"
    
    # Success responses
    @classmethod
    def greeting(cls, hostname: str) -> str:
        """220 Service ready"""
        return cls.format_reply(cls.CODE_READY, f"{hostname} ESMTP Service ready")
    
    @classmethod
    def ok(cls, message: str = "OK") -> str:
        """250 Requested action okay, completed"""
        return cls.format_reply(cls.CODE_OK, message)
    
    @classmethod
    def auth_success(cls) -> str:
        """235 Authentication successful"""
        return cls.format_reply(cls.CODE_AUTH_SUCCESS, "Authentication successful")
    
    @classmethod
    def auth_continue(cls, challenge: str = "") -> str:
        """334 Server challenge"""
        return f"334 {challenge}\r\n"
    
    @classmethod
    def start_data(cls) -> str:
        """354 Start mail input"""
        return cls.format_reply(cls.CODE_START_MAIL, "End data with <CRLF>.<CRLF>")
    
    @classmethod
    def closing(cls, hostname: str) -> str:
        """221 Service closing transmission channel"""
        return cls.format_reply(cls.CODE_CLOSING, f"{hostname} closing connection")
    
    @classmethod
    def help(cls, commands: List[str] = None) -> str:
        """214 Help message"""
        if commands:
            return cls.format_reply(cls.CODE_HELP, "Help available", commands)
        else:
            default_commands = [
                "Commands supported:",
                "HELO EHLO MAIL RCPT DATA",
                "RSET NOOP QUIT HELP"
            ]
            return cls.format_reply(cls.CODE_HELP, default_commands[-1], default_commands[:-1])
    
    # EHLO responses
    @classmethod
    def ehlo(cls, hostname: str, peer_ip: str, extensions: List[str]) -> str:
        """250 EHLO response with extensions"""
        lines = [f"{hostname} Hello {peer_ip}"]
        lines.extend(extensions)
        return cls.format_reply(cls.CODE_OK, lines[-1], lines[:-1])
    
    # Error responses
    @classmethod
    def syntax_error(cls, message: str = "Syntax error") -> str:
        """500 Syntax error, command unrecognized"""
        return cls.format_reply(cls.CODE_SYNTAX_ERROR, message)
    
    @classmethod
    def syntax_error_param(cls, message: str = "Syntax error in parameters") -> str:
        """501 Syntax error in parameters or arguments"""
        return cls.format_reply(cls.CODE_SYNTAX_ERROR_PARAM, message)
    
    @classmethod
    def not_implemented(cls, command: str) -> str:
        """502 Command not implemented"""
        return cls.format_reply(cls.CODE_NOT_IMPLEMENTED, f"Command {command} not implemented")
    
    @classmethod
    def bad_sequence(cls, message: str = "Bad sequence of commands") -> str:
        """503 Bad sequence of commands"""
        return cls.format_reply(cls.CODE_BAD_SEQUENCE, message)
    
    @classmethod
    def auth_required(cls) -> str:
        """530 Authentication required"""
        return cls.format_reply(cls.CODE_AUTH_REQUIRED, "Authentication required")
    
    @classmethod
    def auth_failed(cls) -> str:
        """535 Authentication credentials invalid"""
        return cls.format_reply(cls.CODE_AUTH_FAILED, "Authentication credentials invalid")
    
    @classmethod
    def mailbox_not_found(cls, message: str = "Mailbox not found") -> str:
        """550 Requested action not taken"""
        return cls.format_reply(cls.CODE_MAILBOX_NOT_FOUND, message)
    
    @classmethod
    def exceeded_storage(cls, message: str = "Exceeded storage allocation") -> str:
        """552 Exceeded storage allocation"""
        return cls.format_reply(cls.CODE_EXCEEDED_STORAGE, message)
    
    @classmethod
    def service_not_available(cls, message: str = "Service not available") -> str:
        """421 Service not available, closing transmission channel"""
        return cls.format_reply(cls.CODE_SERVICE_NOT_AVAILABLE, message)
    
    @classmethod
    def local_error(cls, message: str = "Local error in processing") -> str:
        """451 Requested action aborted: local error in processing"""
        return cls.format_reply(cls.CODE_LOCAL_ERROR, message)
    
    @classmethod
    def transaction_failed(cls, message: str = "Transaction failed") -> str:
        """554 Transaction failed"""
        return cls.format_reply(cls.CODE_TRANSACTION_FAILED, message)
    
    @classmethod
    def cannot_vrfy(cls) -> str:
        """252 Cannot VRFY user, but will accept message"""
        return cls.format_reply(cls.CODE_CANNOT_VRFY, "Cannot VRFY user, but will accept message")
    
    # Specialized responses
    @classmethod
    def message_accepted(cls, queue_id: str) -> str:
        """250 Message accepted for delivery"""
        return cls.format_reply(cls.CODE_OK, f"Message accepted for delivery (Queue ID: {queue_id})")
    
    @classmethod
    def sender_ok(cls, sender: str) -> str:
        """250 Sender OK"""
        return cls.format_reply(cls.CODE_OK, f"Sender <{sender}> OK")
    
    @classmethod
    def recipient_ok(cls, recipient: str) -> str:
        """250 Recipient OK"""
        return cls.format_reply(cls.CODE_OK, f"Recipient <{recipient}> OK")
    
    @classmethod
    def reset_ok(cls) -> str:
        """250 Reset OK"""
        return cls.format_reply(cls.CODE_OK, "Reset OK")
    
    @classmethod
    def noop_ok(cls) -> str:
        """250 OK"""
        return cls.format_reply(cls.CODE_OK, "OK")
    
    @classmethod
    def starttls_ready(cls) -> str:
        """220 Ready to start TLS"""
        return cls.format_reply(cls.CODE_READY, "Ready to start TLS")
    
    @classmethod
    def rate_limited(cls) -> str:
        """450 Rate limit exceeded"""
        return cls.format_reply(cls.CODE_MAILBOX_UNAVAILABLE, "Rate limit exceeded, try again later")
    
    @classmethod
    def policy_rejected(cls, reason: str) -> str:
        """550 Rejected by policy"""
        return cls.format_reply(cls.CODE_MAILBOX_NOT_FOUND, f"Rejected by policy: {reason}")
    
    @classmethod
    def greylisted(cls) -> str:
        """450 Greylisted"""
        return cls.format_reply(cls.CODE_MAILBOX_UNAVAILABLE, "Greylisted, try again later")
