"""
Main MTA Application - RFC 5321 Compliant Mail Transfer Agent
MVC Architecture with Controllers, Services, and Repositories
"""
import asyncio
import logging
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Thread

from flask import Flask

import config

# Repositories
from repositories.user_repository import UserRepository
from repositories.queue_repository import QueueRepository
from repositories.policy_repository import PolicyRepository

# Services
from services.auth_service import AuthService
from services.queue_service import QueueService
from services.policy_service import PolicyService
from services.delivery_service import DeliveryService

# Controllers
from controllers.smtp_controller import SMTPController
from controllers.admin_controller import create_admin_blueprint
from controllers.delivery_controller import DeliveryController


# Setup logging
def setup_logging():
    """Configure logging with file rotation"""
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG if config.DEBUG_MODE else logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if config.DEBUG_MODE else logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # SMTP protocol logger (detailed)
    if config.SMTP_LOG_ENABLED:
        smtp_handler = RotatingFileHandler(
            config.SMTP_LOG_FILE,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT
        )
        smtp_handler.setFormatter(formatter)
        smtp_logger = logging.getLogger('smtp_server')
        smtp_logger.addHandler(smtp_handler)
    
    logging.info("Logging configured")


# Global state
shutdown_event = asyncio.Event()
smtp_servers = []
delivery_controller = None


async def start_smtp_server(port: int, is_submission: bool, 
                           smtp_controller: SMTPController):
    """Start SMTP server on specified port"""
    async def client_handler(reader, writer):
        await smtp_controller.handle_session(
            reader, writer,
            config.HOSTNAME,
            is_submission
        )
    
    server = await asyncio.start_server(
        client_handler,
        config.SMTP_BIND_ADDRESS,
        port
    )
    
    role = "Submission" if is_submission else "Relay"
    addr = server.sockets[0].getsockname()
    logging.info(f"SMTP {role} server started on {addr[0]}:{addr[1]}")
    
    return server


async def main_async():
    """Main async application with MVC architecture"""
    global smtp_servers, delivery_controller
    
    logging.info("=" * 60)
    logging.info(f"Starting MTA: {config.HOSTNAME}")
    logging.info(f"Domain: {config.DOMAIN}")
    logging.info(f"Architecture: MVC (Model-View-Controller)")
    logging.info("=" * 60)
    
    # Initialize Repositories
    logging.info("Initializing repositories...")
    user_repo = UserRepository(config.USER_DB_FILE)
    queue_repo = QueueRepository(config.QUEUE_DB_FILE, str(config.QUEUE_DIR))
    policy_repo = PolicyRepository(config.DATA_DIR)
    
    # Initialize Services
    logging.info("Initializing services...")
    auth_service = AuthService(
        user_repo,
        max_attempts=config.MAX_AUTH_ATTEMPTS,
        lockout_duration=config.AUTH_LOCKOUT_DURATION
    )
    queue_service = QueueService(queue_repo)
    policy_service = PolicyService(policy_repo)
    delivery_service = DeliveryService(queue_service)
    
    # Initialize Controllers
    logging.info("Initializing controllers...")
    smtp_controller = SMTPController(auth_service, queue_service, policy_service)
    delivery_controller = DeliveryController(queue_service, delivery_service)
    
    # Start delivery workers
    logging.info(f"Starting {config.DELIVERY_WORKERS} delivery workers...")
    await delivery_controller.start()
    
    # Start SMTP servers
    logging.info("Starting SMTP servers...")
    
    # Port 25 - Relay (MTA-to-MTA)
    if config.SMTP_PORT_RELAY:
        relay_server = await start_smtp_server(
            config.SMTP_PORT_RELAY, False, smtp_controller
        )
        smtp_servers.append(relay_server)
    
    # Port 587 - Submission (MSA)
    if config.SMTP_PORT_SUBMISSION:
        submission_server = await start_smtp_server(
            config.SMTP_PORT_SUBMISSION, True, smtp_controller
        )
        smtp_servers.append(submission_server)
    
    # Start admin API in separate thread
    if config.ADMIN_API_ENABLED:
        logging.info(f"Starting admin API on port {config.ADMIN_API_PORT}...")
        
        admin_app = Flask(__name__)
        admin_app.config['JSON_SORT_KEYS'] = False
        
        # Register admin blueprint
        admin_bp = create_admin_blueprint(auth_service, queue_service, policy_service)
        admin_app.register_blueprint(admin_bp)
        
        def run_flask():
            admin_app.run(
                host='0.0.0.0',
                port=config.ADMIN_API_PORT,
                debug=False,
                use_reloader=False
            )
        
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
    
    logging.info("=" * 60)
    logging.info("MTA is ready and accepting connections")
    logging.info(f"SMTP Relay: port {config.SMTP_PORT_RELAY}")
    logging.info(f"SMTP Submission: port {config.SMTP_PORT_SUBMISSION}")
    if config.ADMIN_API_ENABLED:
        logging.info(f"Admin API: http://localhost:{config.ADMIN_API_PORT}")
    logging.info("=" * 60)
    
    # Wait for shutdown signal
    await shutdown_event.wait()
    
    # Cleanup
    logging.info("Shutting down...")
    
    # Stop SMTP servers
    for server in smtp_servers:
        server.close()
        await server.wait_closed()
    
    # Stop delivery workers
    if delivery_controller:
        await delivery_controller.stop()
    
    logging.info("MTA shutdown complete")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logging.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()


def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Banner
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   RFC 5321 Compliant Mail Transfer Agent (MTA)               ║
║   Version 2.0.0 - MVC Architecture                           ║
║                                                               ║
║   Architecture:                                               ║
║   • Models: Domain entities & business objects               ║
║   • Views: Response formatting (SMTP, JSON, Metrics)         ║
║   • Controllers: Request handlers & orchestration            ║
║   • Services: Business logic layer                           ║
║   • Repositories: Data access abstraction                    ║
║                                                               ║
║   Features:                                                   ║
║   • SMTP/ESMTP on ports 25, 587                              ║
║   • TLS/STARTTLS support (RFC 3207)                          ║
║   • SMTP AUTH (RFC 4954)                                     ║
║   • Persistent queue with retry logic                        ║
║   • Rate limiting & anti-abuse                               ║
║   • Admin REST API                                           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Run async main
        if sys.platform == 'win32':
            # Windows requires ProactorEventLoop for subprocess
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(main_async())
    
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
    except Exception as e:
        logging.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

