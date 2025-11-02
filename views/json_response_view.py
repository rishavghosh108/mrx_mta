"""
JSON Response View - Format JSON API responses
"""
from typing import Any, Dict, List, Optional
from datetime import datetime


class JSONResponseView:
    """
    Format JSON API responses with consistent structure
    """
    
    @staticmethod
    def success(data: Any = None, message: str = None) -> Dict[str, Any]:
        """
        Format success response
        
        Args:
            data: Response data
            message: Optional success message
            
        Returns:
            Dictionary for JSON serialization
        """
        response = {
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
        
        if message:
            response['message'] = message
        
        if data is not None:
            response['data'] = data
        
        return response
    
    @staticmethod
    def error(message: str, code: str = None, details: Any = None) -> Dict[str, Any]:
        """
        Format error response
        
        Args:
            message: Error message
            code: Optional error code
            details: Optional additional error details
            
        Returns:
            Dictionary for JSON serialization
        """
        response = {
            'success': False,
            'error': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if code:
            response['error_code'] = code
        
        if details:
            response['details'] = details
        
        return response
    
    @staticmethod
    def paginated(items: List[Any], total: int, page: int = 1, 
                  per_page: int = 100) -> Dict[str, Any]:
        """
        Format paginated response
        
        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            per_page: Items per page
            
        Returns:
            Dictionary for JSON serialization
        """
        return {
            'success': True,
            'data': items,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page,
                'count': len(items)
            },
            'timestamp': datetime.now().isoformat()
        }
    
    # Queue-specific responses
    @staticmethod
    def queue_message(queued_msg) -> Dict[str, Any]:
        """Format queue message for API response"""
        return {
            'queue_id': queued_msg.queue_id,
            'sender': queued_msg.message.sender,
            'recipients': queued_msg.message.recipients,
            'status': queued_msg.status,
            'attempts': queued_msg.attempts,
            'created_at': datetime.fromtimestamp(queued_msg.created_at).isoformat(),
            'next_retry_at': datetime.fromtimestamp(queued_msg.next_retry_at).isoformat() 
                            if queued_msg.next_retry_at else None,
            'last_error': queued_msg.last_error,
            'recipient_status': queued_msg.recipient_status
        }
    
    @staticmethod
    def queue_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
        """Format queue statistics"""
        return JSONResponseView.success({
            'total_messages': stats.get('total', 0),
            'by_status': stats.get('by_status', {}),
            'pending': stats.get('pending', 0),
            'completed': stats.get('completed', 0),
            'oldest_message': datetime.fromtimestamp(stats['oldest']).isoformat() 
                            if stats.get('oldest') else None,
            'newest_message': datetime.fromtimestamp(stats['newest']).isoformat() 
                            if stats.get('newest') else None
        })
    
    # User-specific responses
    @staticmethod
    def user(user) -> Dict[str, Any]:
        """Format user for API response"""
        return {
            'username': user.username,
            'enabled': user.enabled,
            'admin': user.admin,
            'rate_limit': user.rate_limit,
            'created_at': datetime.fromtimestamp(user.created_at).isoformat(),
            'last_login': datetime.fromtimestamp(user.last_login).isoformat() 
                        if user.last_login else None,
            'login_count': user.login_count
        }
    
    @staticmethod
    def user_list(users: List) -> Dict[str, Any]:
        """Format list of users"""
        return JSONResponseView.success([
            JSONResponseView.user(user) for user in users
        ])
    
    # Policy-specific responses
    @staticmethod
    def blacklist(items: List[str]) -> Dict[str, Any]:
        """Format blacklist"""
        return JSONResponseView.success({
            'blacklist': items,
            'count': len(items)
        })
    
    @staticmethod
    def whitelist(items: List[str]) -> Dict[str, Any]:
        """Format whitelist"""
        return JSONResponseView.success({
            'whitelist': items,
            'count': len(items)
        })
    
    @staticmethod
    def rate_limit_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
        """Format rate limit statistics"""
        return JSONResponseView.success(stats)
    
    # Config response
    @staticmethod
    def config(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format configuration"""
        return JSONResponseView.success(config_data)
    
    # Health check
    @staticmethod
    def health(healthy: bool = True, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format health check response"""
        response = {
            'status': 'healthy' if healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            response['details'] = details
        
        return response
