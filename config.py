"""
MTA Configuration Module - RFC 5321, 6409, 3207, 4954 Compliant
Comprehensive settings for production-ready Mail Transfer Agent
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
QUEUE_DIR = DATA_DIR / 'queue'
MAILDIR = DATA_DIR / 'maildir'
LOG_DIR = BASE_DIR / 'logs'

# Database
DB_PATH = str(DATA_DIR / 'mta.db')

# Ensure directories exist
for directory in [DATA_DIR, QUEUE_DIR, MAILDIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================================
# SMTP Server Configuration (RFC 5321, 6409)
# ============================================================================

# Server identity
HOSTNAME = os.environ.get('MTA_HOSTNAME', 'mail.example.com')
DOMAIN = os.environ.get('MTA_DOMAIN', 'example.com')

# SMTP Ports
# Port 25: MTA-to-MTA relay (incoming mail from other servers)
# Port 587: Message Submission (MSA - requires AUTH)
# Port 465: SMTPS (deprecated but still used, implicit TLS)
SMTP_PORT_RELAY = int(os.environ.get('MTA_PORT_RELAY', '25'))
SMTP_PORT_SUBMISSION = int(os.environ.get('MTA_PORT_SUBMISSION', '587'))
SMTP_PORT_SMTPS = int(os.environ.get('MTA_PORT_SMTPS', '465'))

# Bind address
SMTP_BIND_ADDRESS = os.environ.get('MTA_BIND_ADDRESS', '0.0.0.0')

# SMTP Protocol Settings
SMTP_BANNER = f"{HOSTNAME} ESMTP MTA Ready"
SMTP_TIMEOUT = int(os.environ.get('MTA_SMTP_TIMEOUT', '300'))  # 5 minutes
SMTP_MAX_MESSAGE_SIZE = int(os.environ.get('MTA_MAX_MESSAGE_SIZE', str(35 * 1024 * 1024)))  # 35 MB
SMTP_MAX_RECIPIENTS = int(os.environ.get('MTA_MAX_RECIPIENTS', '100'))
SMTP_MAX_HOPS = int(os.environ.get('MTA_MAX_HOPS', '30'))  # Received header count

# ESMTP Extensions to advertise
ESMTP_EXTENSIONS = [
    'STARTTLS',
    'AUTH PLAIN LOGIN',
    'PIPELINING',
    '8BITMIME',
    'DSN',
    'ENHANCEDSTATUSCODES',
    f'SIZE {SMTP_MAX_MESSAGE_SIZE}',
]

# ============================================================================
# TLS/SSL Configuration (RFC 3207)
# ============================================================================

# TLS Certificates
TLS_CERT_FILE = os.environ.get('MTA_TLS_CERT', str(BASE_DIR / 'certs' / 'server.crt'))
TLS_KEY_FILE = os.environ.get('MTA_TLS_KEY', str(BASE_DIR / 'certs' / 'server.key'))
TLS_CA_FILE = os.environ.get('MTA_TLS_CA', None)

# TLS Settings
TLS_REQUIRED_ON_SUBMISSION = os.environ.get('MTA_TLS_REQUIRED_SUBMISSION', 'True').lower() == 'true'
TLS_MINIMUM_VERSION = 'TLSv1.2'  # Enforce TLS 1.2 or higher
TLS_CIPHERS = 'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS'

# ============================================================================
# Authentication (RFC 4954)
# ============================================================================

# Require authentication for submission port
AUTH_REQUIRED_SUBMISSION = os.environ.get('MTA_AUTH_REQUIRED', 'True').lower() == 'true'

# Authentication mechanisms (only PLAIN and LOGIN over TLS for security)
AUTH_MECHANISMS = ['PLAIN', 'LOGIN']

# User database (simple file-based for MVP, replace with LDAP/DB for production)
AUTH_USERS_FILE = str(DATA_DIR / 'users.json')

# Failed authentication lockout
AUTH_MAX_FAILURES = int(os.environ.get('MTA_AUTH_MAX_FAILURES', '5'))
AUTH_LOCKOUT_DURATION = int(os.environ.get('MTA_AUTH_LOCKOUT_DURATION', '300'))  # 5 minutes

# ============================================================================
# Queue Configuration
# ============================================================================

# Queue paths
QUEUE_ACTIVE_DIR = QUEUE_DIR / 'active'
QUEUE_DEFERRED_DIR = QUEUE_DIR / 'deferred'
QUEUE_BOUNCE_DIR = QUEUE_DIR / 'bounce'
QUEUE_CORRUPT_DIR = QUEUE_DIR / 'corrupt'

for qdir in [QUEUE_ACTIVE_DIR, QUEUE_DEFERRED_DIR, QUEUE_BOUNCE_DIR, QUEUE_CORRUPT_DIR]:
    qdir.mkdir(parents=True, exist_ok=True)

# Retry policy (RFC 5321 - exponential backoff)
RETRY_SCHEDULE = [
    5 * 60,      # 5 minutes
    15 * 60,     # 15 minutes
    60 * 60,     # 1 hour
    4 * 60 * 60, # 4 hours
    12 * 60 * 60,# 12 hours
    24 * 60 * 60,# 24 hours
    48 * 60 * 60,# 48 hours
]

MAX_QUEUE_AGE = int(os.environ.get('MTA_MAX_QUEUE_AGE', str(7 * 24 * 60 * 60)))  # 7 days
MAX_RETRIES = len(RETRY_SCHEDULE)

# Queue processing
DELIVERY_WORKERS = int(os.environ.get('MTA_DELIVERY_WORKERS', '10'))
DELIVERY_INTERVAL = float(os.environ.get('MTA_DELIVERY_INTERVAL', '5'))  # seconds

# ============================================================================
# Delivery Configuration
# ============================================================================

# MX Resolution
DNS_TIMEOUT = int(os.environ.get('MTA_DNS_TIMEOUT', '10'))
MX_FALLBACK_TO_A = os.environ.get('MTA_MX_FALLBACK_A', 'True').lower() == 'true'

# Connection settings
SMTP_CONNECT_TIMEOUT = int(os.environ.get('MTA_CONNECT_TIMEOUT', '30'))
SMTP_DATA_TIMEOUT = int(os.environ.get('MTA_DATA_TIMEOUT', '60'))

# Per-destination limits
MAX_CONNECTIONS_PER_DOMAIN = int(os.environ.get('MTA_MAX_CONN_PER_DOMAIN', '5'))
MAX_MESSAGES_PER_CONNECTION = int(os.environ.get('MTA_MAX_MSG_PER_CONN', '10'))

# Relay fallback
RELAY_HOST = os.environ.get('MTA_RELAY_HOST', None)
RELAY_PORT = int(os.environ.get('MTA_RELAY_PORT', '25'))

# ============================================================================
# SPF/DKIM/DMARC Configuration
# ============================================================================

# SPF (RFC 7208)
SPF_ENABLED = os.environ.get('MTA_SPF_ENABLED', 'True').lower() == 'true'
SPF_REJECT_FAIL = os.environ.get('MTA_SPF_REJECT_FAIL', 'False').lower() == 'true'

# DKIM (RFC 6376)
DKIM_ENABLED = os.environ.get('MTA_DKIM_ENABLED', 'True').lower() == 'true'
DKIM_SELECTOR = os.environ.get('MTA_DKIM_SELECTOR', 'default')
DKIM_PRIVATE_KEY = str(DATA_DIR / 'dkim' / f'{DKIM_SELECTOR}.private')
DKIM_SIGN_HEADERS = [
    'From', 'To', 'Subject', 'Date', 'Message-ID',
    'References', 'In-Reply-To', 'Reply-To'
]

# DMARC (RFC 7489)
DMARC_ENABLED = os.environ.get('MTA_DMARC_ENABLED', 'True').lower() == 'true'

# ============================================================================
# Anti-Abuse & Policy
# ============================================================================

# Rate limiting
RATE_LIMIT_PER_IP = int(os.environ.get('MTA_RATE_LIMIT_IP', '100'))  # messages/hour
RATE_LIMIT_PER_USER = int(os.environ.get('MTA_RATE_LIMIT_USER', '200'))  # messages/hour
RATE_LIMIT_PER_DOMAIN = int(os.environ.get('MTA_RATE_LIMIT_DOMAIN', '1000'))  # messages/hour

# Connection limits
MAX_CONNECTIONS_PER_IP = int(os.environ.get('MTA_MAX_CONN_PER_IP', '10'))
MAX_CONNECTIONS_GLOBAL = int(os.environ.get('MTA_MAX_CONN_GLOBAL', '1000'))

# RBL (Realtime Blackhole List)
RBL_ENABLED = os.environ.get('MTA_RBL_ENABLED', 'False').lower() == 'true'
RBL_SERVERS = os.environ.get('MTA_RBL_SERVERS', 'zen.spamhaus.org,bl.spamcop.net').split(',')

# Greylisting
GREYLIST_ENABLED = os.environ.get('MTA_GREYLIST_ENABLED', 'False').lower() == 'true'
GREYLIST_DELAY = int(os.environ.get('MTA_GREYLIST_DELAY', '300'))  # 5 minutes

# Content filtering
SPAM_FILTER_ENABLED = os.environ.get('MTA_SPAM_FILTER', 'False').lower() == 'true'
VIRUS_SCAN_ENABLED = os.environ.get('MTA_VIRUS_SCAN', 'False').lower() == 'true'

# ============================================================================
# Bounce & DSN Configuration (RFC 3464)
# ============================================================================

BOUNCE_SENDER = os.environ.get('MTA_BOUNCE_SENDER', f'MAILER-DAEMON@{DOMAIN}')
POSTMASTER_ADDRESS = os.environ.get('MTA_POSTMASTER', f'postmaster@{DOMAIN}')

# Prevent backscatter
BOUNCE_VERIFY_SENDER = os.environ.get('MTA_BOUNCE_VERIFY', 'True').lower() == 'true'

# ============================================================================
# Local Delivery
# ============================================================================

LOCAL_DOMAINS = os.environ.get('MTA_LOCAL_DOMAINS', DOMAIN).split(',')
LOCAL_DELIVERY_METHOD = os.environ.get('MTA_LOCAL_DELIVERY', 'maildir')  # maildir, lmtp, custom

# LMTP settings (if using LMTP for local delivery)
LMTP_HOST = os.environ.get('MTA_LMTP_HOST', 'localhost')
LMTP_PORT = int(os.environ.get('MTA_LMTP_PORT', '24'))

# ============================================================================
# Logging & Monitoring
# ============================================================================

LOG_LEVEL = os.environ.get('MTA_LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(queue_id)s] - %(message)s'
LOG_FILE = str(LOG_DIR / 'mta.log')
LOG_MAX_BYTES = int(os.environ.get('MTA_LOG_MAX_BYTES', str(100 * 1024 * 1024)))  # 100 MB
LOG_BACKUP_COUNT = int(os.environ.get('MTA_LOG_BACKUP_COUNT', '10'))

# SMTP transaction logging (wire protocol)
SMTP_LOG_ENABLED = os.environ.get('MTA_SMTP_LOG_ENABLED', 'True').lower() == 'true'
SMTP_LOG_FILE = str(LOG_DIR / 'smtp.log')

# Metrics
METRICS_ENABLED = os.environ.get('MTA_METRICS_ENABLED', 'True').lower() == 'true'
METRICS_PORT = int(os.environ.get('MTA_METRICS_PORT', '9090'))

# ============================================================================
# Admin API
# ============================================================================

ADMIN_API_ENABLED = os.environ.get('MTA_ADMIN_API', 'True').lower() == 'true'
ADMIN_API_PORT = int(os.environ.get('MTA_ADMIN_PORT', '8080'))
ADMIN_API_TOKEN = os.environ.get('MTA_ADMIN_TOKEN', 'change-me-in-production')

# ============================================================================
# Security
# ============================================================================

# Open relay prevention
RELAY_ALLOWED_NETWORKS = os.environ.get('MTA_RELAY_NETWORKS', '127.0.0.0/8,::1/128').split(',')

# Header injection prevention
HEADER_MAX_LENGTH = int(os.environ.get('MTA_HEADER_MAX_LENGTH', '998'))  # RFC 5322
HEADER_MAX_COUNT = int(os.environ.get('MTA_HEADER_MAX_COUNT', '1000'))

# Command limits
SMTP_MAX_UNKNOWN_COMMANDS = int(os.environ.get('MTA_MAX_UNKNOWN_CMDS', '5'))
SMTP_MAX_ERRORS = int(os.environ.get('MTA_MAX_ERRORS', '3'))

# ============================================================================
# Development/Testing
# ============================================================================

DEBUG_MODE = os.environ.get('MTA_DEBUG', 'False').lower() == 'true'
TEST_MODE = os.environ.get('MTA_TEST_MODE', 'False').lower() == 'true'
