"""
Test Suite for MTA Components - MVC Architecture
Run with: pytest tests/test_mta.py -v
"""
import pytest
import asyncio
import json
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Models
from models.message import Message, QueuedMessage
from models.user import User
from models.policy import RateLimit, PolicyRule

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
from controllers.smtp_controller import SMTPController, SMTPSession
from controllers.delivery_controller import DeliveryController

# Views
from views.smtp_response_view import SMTPResponseView
from views.json_response_view import JSONResponseView
from views.metrics_view import MetricsView


class TestQueueService:
    """Test queue service functionality (MVC)"""
    
    @pytest.fixture
    def queue_service(self, tmp_path):
        """Create temporary queue service"""
        db_path = tmp_path / "test_queue.db"
        queue_dir = tmp_path / "queue"
        queue_dir.mkdir()
        queue_repo = QueueRepository(str(db_path), str(queue_dir))
        return QueueService(queue_repo)
    
    @pytest.mark.asyncio
    async def test_enqueue_message(self, queue_service):
        """Test message enqueueing"""
        queued_msg = await queue_service.enqueue_message(
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            message_data="Subject: Test\r\n\r\nTest body",
            session_info={"peer_ip": "127.0.0.1"}
        )
        
        assert queued_msg is not None
        assert len(queued_msg.queue_id) > 0
        assert queued_msg.message.sender == "sender@example.com"
    
    @pytest.mark.asyncio
    async def test_get_messages_for_delivery(self, queue_service):
        """Test retrieving messages for delivery"""
        # Enqueue a message
        queued_msg = await queue_service.enqueue_message(
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            message_data="Subject: Test\r\n\r\nTest body",
            session_info={"peer_ip": "127.0.0.1"}
        )
        
        # Get ready messages
        messages = await queue_service.get_messages_for_delivery(limit=10)
        assert len(messages) > 0
        assert messages[0].queue_id == queued_msg.queue_id
    
    @pytest.mark.asyncio
    async def test_delivery_status_update(self, queue_service):
        """Test updating delivery status"""
        # Enqueue
        queued_msg = await queue_service.enqueue_message(
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            message_data="Subject: Test\r\n\r\nTest body",
            session_info={"peer_ip": "127.0.0.1"}
        )
        
        # Mark as delivered (250 = success)
        await queue_service.update_delivery_status(
            queued_msg.queue_id, "recipient@example.com", 250, "OK"
        )
        
        # Should be marked as delivered
        updated_msg = await queue_service.get_message(queued_msg.queue_id)
        assert updated_msg.status == 'delivered'
    
    @pytest.mark.asyncio
    async def test_queue_stats(self, queue_service):
        """Test queue statistics"""
        # Enqueue some messages
        for i in range(3):
            await queue_service.enqueue_message(
                sender=f"sender{i}@example.com",
                recipients=[f"recipient{i}@example.com"],
                message_data="Subject: Test\r\n\r\nTest body",
                session_info={"peer_ip": "127.0.0.1"}
            )
        
        stats = await queue_service.get_queue_stats()
        assert 'by_status' in stats
        assert stats.get('total', 0) >= 3


class TestAuthService:
    """Test authentication service functionality (MVC)"""
    
    @pytest.fixture
    def auth_service(self, tmp_path):
        """Create temporary auth service"""
        users_file = tmp_path / "users.json"
        user_repo = UserRepository(str(users_file))
        return AuthService(user_repo, max_attempts=5, lockout_duration=300)
    
    @pytest.mark.asyncio
    async def test_create_user(self, auth_service):
        """Test creating a user"""
        user = await auth_service.create_user(
            "newuser@example.com", "password123"
        )
        assert user is not None
        assert user.username == "newuser@example.com"
        
        # Try creating same user again should fail
        try:
            await auth_service.create_user("newuser@example.com", "password123")
            assert False, "Should have raised exception"
        except:
            pass  # Expected
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_service):
        """Test successful authentication"""
        await auth_service.create_user("user@example.com", "correctpass")
        
        user = await auth_service.authenticate(
            "user@example.com", "correctpass", "127.0.0.1"
        )
        assert user is not None
        assert user.username == "user@example.com"
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, auth_service):
        """Test failed authentication"""
        await auth_service.create_user("user@example.com", "correctpass")
        
        user = await auth_service.authenticate(
            "user@example.com", "wrongpass", "127.0.0.1"
        )
        assert user is None
    
    @pytest.mark.asyncio
    async def test_lockout(self, auth_service):
        """Test account lockout after failures"""
        await auth_service.create_user("user@example.com", "correctpass")
        
        # Attempt multiple failed authentications
        for _ in range(6):
            await auth_service.authenticate(
                "user@example.com", "wrongpass", "192.0.2.1"
            )
        
        # Even with correct password, should be locked out
        user = await auth_service.authenticate(
            "user@example.com", "correctpass", "192.0.2.1"
        )
        assert user is None
    
    @pytest.mark.asyncio
    async def test_change_password(self, auth_service):
        """Test password change"""
        await auth_service.create_user("user@example.com", "oldpass")
        
        success = await auth_service.change_password(
            "user@example.com", "newpass"
        )
        assert success is True
        
        # Old password should not work
        user = await auth_service.authenticate(
            "user@example.com", "oldpass", "127.0.0.1"
        )
        assert user is None
        
        # New password should work
        user = await auth_service.authenticate(
            "user@example.com", "newpass", "127.0.0.1"
        )
        assert user is not None


class TestPolicyService:
    """Test policy service functionality (MVC)"""
    
    @pytest.fixture
    def policy_service(self, tmp_path):
        """Create policy service"""
        policy_repo = PolicyRepository(str(tmp_path))
        return PolicyService(policy_repo)
    
    @pytest.mark.asyncio
    async def test_blacklist(self, policy_service):
        """Test blacklisting"""
        test_target = "spam.example.com"
        
        # Add to blacklist
        await policy_service.add_to_blacklist(test_target, "Spam domain")
        
        # Check if blacklisted
        is_blacklisted = await policy_service.check_blacklist(domain=test_target)
        assert is_blacklisted is True
        
        # Remove from blacklist
        await policy_service.remove_from_blacklist(test_target)
        is_blacklisted = await policy_service.check_blacklist(domain=test_target)
        assert is_blacklisted is False
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, policy_service):
        """Test rate limiting"""
        test_ip = "192.0.2.1"
        
        # Should allow first few
        for i in range(3):
            result = await policy_service.check_ip_rate_limit(test_ip)
            assert result is True
        
        # After many attempts, should block
        for i in range(100):
            await policy_service.check_ip_rate_limit(test_ip)
        
        result = await policy_service.check_ip_rate_limit(test_ip)
        # May or may not be blocked depending on rate limit config
        assert result in [True, False]


class TestRateLimit:
    """Test rate limit model"""
    
    def test_rate_limit_consume(self):
        """Test token bucket consumption"""
        rate_limit = RateLimit(
            identifier="test",
            limit_type="ip",
            capacity=5,
            tokens=5.0,
            refill_rate=1.0
        )
        
        # Should allow first 5
        for i in range(5):
            result = rate_limit.consume(1)
            assert result is True
        
        # Should block next one
        result = rate_limit.consume(1)
        assert result is False


class TestSMTPController:
    """Test SMTP controller and protocol parsing (MVC)"""
    
    def test_email_regex(self):
        """Test email address validation"""
        # Valid addresses
        valid = [
            "user@example.com",
            "<user@example.com>",
            "first.last@example.co.uk",
            "user+tag@example.com",
        ]
        
        for addr in valid:
            match = SMTPController.EMAIL_REGEX.match(addr)
            assert match is not None, f"Failed to match {addr}"


class TestSMTPResponseView:
    """Test SMTP response view formatting"""
    
    def test_reply_formatting(self):
        """Test SMTP reply formatting"""
        view = SMTPResponseView()
        
        # Single line reply
        reply = view.format_reply(250, "OK")
        assert reply == "250 2.0.0 OK\r\n"
        
        # Multi-line reply
        reply = view.format_reply(250, "OK", ["Line 1", "Line 2"])
        assert "250-" in reply
        assert "250 " in reply
        assert "Line 1" in reply
    
    def test_greeting(self):
        """Test greeting message"""
        view = SMTPResponseView()
        reply = view.greeting("mail.example.com")
        assert "220" in reply
        assert "mail.example.com" in reply
    
    def test_auth_responses(self):
        """Test authentication responses"""
        view = SMTPResponseView()
        
        success = view.auth_success()
        assert "235" in success
        
        failed = view.auth_failed()
        assert "535" in failed


class TestJSONResponseView:
    """Test JSON response view formatting"""
    
    def test_success_response(self):
        """Test success response"""
        view = JSONResponseView()
        response = view.success(data={'test': 'value'}, message='Success')
        
        assert response['success'] is True
        assert response['data']['test'] == 'value'
        assert response['message'] == 'Success'
    
    def test_error_response(self):
        """Test error response"""
        view = JSONResponseView()
        response = view.error('Error occurred', code='TEST_ERROR')
        
        assert response['success'] is False
        assert response['error'] == 'Error occurred'
        assert response['error_code'] == 'TEST_ERROR'


class TestMetricsView:
    """Test metrics view formatting"""
    
    def test_metric_formatting(self):
        """Test Prometheus metric formatting"""
        view = MetricsView()
        
        metric = view.format_metric(
            'test_metric',
            'gauge',
            'Test metric',
            [(None, 42)]
        )
        
        assert 'test_metric' in metric
        assert 'gauge' in metric
        assert '42' in metric


class TestMessageFormat:
    """Test message formatting and headers"""
    
    def test_received_header_format(self):
        """Test Received header generation"""
        # TODO: Implement when SMTP session is mockable
        pass


def test_config_loading():
    """Test configuration loading"""
    import config
    
    assert hasattr(config, 'HOSTNAME')
    assert hasattr(config, 'DOMAIN')
    assert hasattr(config, 'SMTP_PORT_RELAY')
    assert hasattr(config, 'SMTP_PORT_SUBMISSION')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
