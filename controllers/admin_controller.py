"""
Admin Controller - REST API for administration
"""
import logging
from flask import Blueprint, request, jsonify
from functools import wraps

from services.auth_service import AuthService
from services.queue_service import QueueService
from services.policy_service import PolicyService
from views.json_response_view import JSONResponseView
from views.metrics_view import MetricsView
import config

logger = logging.getLogger(__name__)


def create_admin_blueprint(auth_service: AuthService, 
                          queue_service: QueueService,
                          policy_service: PolicyService) -> Blueprint:
    """
    Create Flask blueprint for admin API
    
    Args:
        auth_service: Authentication service instance
        queue_service: Queue service instance
        policy_service: Policy service instance
        
    Returns:
        Flask Blueprint configured with all admin routes
    """
    bp = Blueprint('admin', __name__)
    view = JSONResponseView()
    metrics_view = MetricsView()
    
    def require_auth(f):
        """Decorator to require admin authentication"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization')
            if not token or not token.startswith('Bearer '):
                return jsonify(view.error('Missing or invalid authorization', 'AUTH_MISSING')), 401
            
            provided_token = token[7:]  # Remove 'Bearer '
            if provided_token != config.ADMIN_API_TOKEN:
                return jsonify(view.error('Invalid token', 'AUTH_INVALID')), 403
            
            return f(*args, **kwargs)
        return decorated
    
    # Health check (no auth required)
    @bp.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify(view.health()), 200
    
    # Queue Management
    @bp.route('/api/queue/stats', methods=['GET'])
    @require_auth
    async def queue_stats():
        """Get queue statistics"""
        try:
            stats = await queue_service.get_queue_stats()
            return jsonify(view.queue_stats(stats)), 200
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return jsonify(view.error(str(e), 'QUEUE_ERROR')), 500
    
    @bp.route('/api/queue/messages', methods=['GET'])
    @require_auth
    async def list_queue():
        """List queued messages"""
        try:
            limit = request.args.get('limit', 100, type=int)
            status = request.args.get('status', 'active')
            
            if status == 'ready':
                messages = await queue_service.get_messages_for_delivery(limit=limit)
            else:
                messages = await queue_service.get_messages_by_status(status, limit=limit)
            
            result = [view.queue_message(msg) for msg in messages]
            
            return jsonify(view.success({
                'messages': result,
                'count': len(result)
            })), 200
        
        except Exception as e:
            logger.error(f"Error listing queue: {e}")
            return jsonify(view.error(str(e), 'QUEUE_ERROR')), 500
    
    @bp.route('/api/queue/message/<queue_id>', methods=['GET'])
    @require_auth
    async def get_message(queue_id):
        """Get message details"""
        try:
            message = await queue_service.get_message(queue_id)
            
            if message is None:
                return jsonify(view.error('Message not found', 'NOT_FOUND')), 404
            
            return jsonify(view.success(view.queue_message(message))), 200
        
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return jsonify(view.error(str(e), 'QUEUE_ERROR')), 500
    
    @bp.route('/api/queue/message/<queue_id>/requeue', methods=['POST'])
    @require_auth
    async def requeue_message(queue_id):
        """Requeue a message for immediate delivery"""
        try:
            success = await queue_service.requeue_message(queue_id)
            
            if not success:
                return jsonify(view.error('Message not found', 'NOT_FOUND')), 404
            
            return jsonify(view.success(message='Message requeued')), 200
        
        except Exception as e:
            logger.error(f"Error requeuing message: {e}")
            return jsonify(view.error(str(e), 'QUEUE_ERROR')), 500
    
    @bp.route('/api/queue/message/<queue_id>', methods=['DELETE'])
    @require_auth
    async def delete_message(queue_id):
        """Delete a message from queue"""
        try:
            success = await queue_service.delete_message(queue_id)
            
            if not success:
                return jsonify(view.error('Message not found', 'NOT_FOUND')), 404
            
            return jsonify(view.success(message='Message deleted')), 200
        
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return jsonify(view.error(str(e), 'QUEUE_ERROR')), 500
    
    # Policy Management
    @bp.route('/api/policy/blacklist', methods=['GET'])
    @require_auth
    async def get_blacklist():
        """Get blacklist entries"""
        try:
            # Get blacklist from repository
            blacklist = await policy_service.policy_repo.get_blacklist()
            return jsonify(view.blacklist(blacklist)), 200
        except Exception as e:
            logger.error(f"Error getting blacklist: {e}")
            return jsonify(view.error(str(e), 'POLICY_ERROR')), 500
    
    @bp.route('/api/policy/blacklist', methods=['POST'])
    @require_auth
    async def add_blacklist():
        """Add to blacklist"""
        try:
            data = request.get_json()
            target = data.get('target')
            reason = data.get('reason')
            
            if not target:
                return jsonify(view.error('Target required', 'INVALID_REQUEST')), 400
            
            await policy_service.add_to_blacklist(target, reason)
            return jsonify(view.success(message=f'Added {target} to blacklist')), 201
        
        except Exception as e:
            logger.error(f"Error adding to blacklist: {e}")
            return jsonify(view.error(str(e), 'POLICY_ERROR')), 500
    
    @bp.route('/api/policy/blacklist/<target>', methods=['DELETE'])
    @require_auth
    async def remove_blacklist(target):
        """Remove from blacklist"""
        try:
            success = await policy_service.remove_from_blacklist(target)
            
            if not success:
                return jsonify(view.error('Entry not found', 'NOT_FOUND')), 404
            
            return jsonify(view.success(message=f'Removed {target} from blacklist')), 200
        
        except Exception as e:
            logger.error(f"Error removing from blacklist: {e}")
            return jsonify(view.error(str(e), 'POLICY_ERROR')), 500
    
    @bp.route('/api/policy/rate-limits', methods=['GET'])
    @require_auth
    async def get_rate_limits():
        """Get rate limit statistics"""
        try:
            stats = await policy_service.get_rate_limit_stats()
            return jsonify(view.rate_limit_stats(stats)), 200
        except Exception as e:
            logger.error(f"Error getting rate limits: {e}")
            return jsonify(view.error(str(e), 'POLICY_ERROR')), 500
    
    # User Management
    @bp.route('/api/users', methods=['GET'])
    @require_auth
    async def list_users():
        """List all users"""
        try:
            users = await auth_service.list_users()
            return jsonify(view.user_list(users)), 200
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return jsonify(view.error(str(e), 'USER_ERROR')), 500
    
    @bp.route('/api/users', methods=['POST'])
    @require_auth
    async def create_user():
        """Create new user"""
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify(view.error('Username and password required', 'INVALID_REQUEST')), 400
            
            # Optional fields
            rate_limit = data.get('rate_limit')
            admin = data.get('admin', False)
            enabled = data.get('enabled', True)
            
            user = await auth_service.create_user(
                username, password, 
                rate_limit=rate_limit, 
                admin=admin, 
                enabled=enabled
            )
            
            return jsonify(view.success(view.user(user), 'User created')), 201
        
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return jsonify(view.error(str(e), 'USER_ERROR')), 500
    
    @bp.route('/api/users/<username>', methods=['GET'])
    @require_auth
    async def get_user(username):
        """Get user details"""
        try:
            user = await auth_service.get_user(username)
            
            if user is None:
                return jsonify(view.error('User not found', 'NOT_FOUND')), 404
            
            return jsonify(view.success(view.user(user))), 200
        
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return jsonify(view.error(str(e), 'USER_ERROR')), 500
    
    @bp.route('/api/users/<username>', methods=['PUT'])
    @require_auth
    async def update_user(username):
        """Update user"""
        try:
            data = request.get_json()
            
            # Remove password from updates (use separate endpoint)
            if 'password' in data:
                del data['password']
            
            success = await auth_service.update_user(username, **data)
            
            if not success:
                return jsonify(view.error('User not found', 'NOT_FOUND')), 404
            
            return jsonify(view.success(message='User updated')), 200
        
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return jsonify(view.error(str(e), 'USER_ERROR')), 500
    
    @bp.route('/api/users/<username>', methods=['DELETE'])
    @require_auth
    async def delete_user(username):
        """Delete user"""
        try:
            success = await auth_service.delete_user(username)
            
            if not success:
                return jsonify(view.error('User not found', 'NOT_FOUND')), 404
            
            return jsonify(view.success(message='User deleted')), 200
        
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return jsonify(view.error(str(e), 'USER_ERROR')), 500
    
    @bp.route('/api/users/<username>/password', methods=['PUT'])
    @require_auth
    async def change_password(username):
        """Change user password"""
        try:
            data = request.get_json()
            new_password = data.get('password')
            
            if not new_password:
                return jsonify(view.error('Password required', 'INVALID_REQUEST')), 400
            
            success = await auth_service.change_password(username, new_password)
            
            if not success:
                return jsonify(view.error('User not found', 'NOT_FOUND')), 404
            
            return jsonify(view.success(message='Password changed')), 200
        
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return jsonify(view.error(str(e), 'USER_ERROR')), 500
    
    # Configuration
    @bp.route('/api/config', methods=['GET'])
    @require_auth
    def get_config():
        """Get current configuration"""
        config_data = {
            'hostname': config.HOSTNAME,
            'domain': config.DOMAIN,
            'smtp_ports': {
                'relay': config.SMTP_PORT_RELAY,
                'submission': config.SMTP_PORT_SUBMISSION,
            },
            'limits': {
                'max_message_size': config.SMTP_MAX_MESSAGE_SIZE,
                'max_recipients': config.SMTP_MAX_RECIPIENTS,
                'rate_limit_per_ip': config.RATE_LIMIT_PER_IP,
                'rate_limit_per_user': config.RATE_LIMIT_PER_USER,
            },
            'features': {
                'spf_enabled': config.SPF_ENABLED,
                'dkim_enabled': config.DKIM_ENABLED,
                'dmarc_enabled': config.DMARC_ENABLED,
                'rbl_enabled': config.RBL_ENABLED,
                'greylist_enabled': config.GREYLIST_ENABLED,
            }
        }
        
        return jsonify(view.config(config_data)), 200
    
    # Metrics
    @bp.route('/api/metrics', methods=['GET'])
    def metrics():
        """Prometheus-compatible metrics endpoint"""
        try:
            # Import asyncio for running async functions
            import asyncio
            
            # Get queue stats
            queue_stats_data = asyncio.run(queue_service.get_queue_stats())
            queue_metrics = metrics_view.queue_metrics(queue_stats_data)
            
            # Get rate limit stats
            rate_stats_data = asyncio.run(policy_service.get_rate_limit_stats())
            rate_metrics = metrics_view.rate_limit_metrics(rate_stats_data)
            
            # Combine all metrics
            all_metrics = metrics_view.combine_metrics(queue_metrics, rate_metrics)
            
            return all_metrics, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return f"# Error generating metrics: {e}\n", 500, {'Content-Type': 'text/plain'}
    
    return bp
