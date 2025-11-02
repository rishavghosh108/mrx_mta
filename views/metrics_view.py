"""
Metrics View - Format Prometheus-compatible metrics
"""
from typing import Dict, Any, List


class MetricsView:
    """
    Format metrics in Prometheus exposition format
    """
    
    @staticmethod
    def format_metric(name: str, metric_type: str, help_text: str, 
                     values: List[tuple]) -> str:
        """
        Format a single metric in Prometheus format
        
        Args:
            name: Metric name
            metric_type: Metric type (gauge, counter, histogram, summary)
            help_text: Metric description
            values: List of (labels_dict, value) tuples
            
        Returns:
            Formatted metric string
        """
        lines = []
        
        # Help text
        lines.append(f"# HELP {name} {help_text}")
        
        # Type
        lines.append(f"# TYPE {name} {metric_type}")
        
        # Values
        for labels, value in values:
            if labels:
                label_str = ','.join([f'{k}="{v}"' for k, v in labels.items()])
                lines.append(f"{name}{{{label_str}}} {value}")
            else:
                lines.append(f"{name} {value}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def queue_metrics(stats: Dict[str, Any]) -> str:
        """
        Format queue statistics as Prometheus metrics
        
        Args:
            stats: Queue statistics dictionary
            
        Returns:
            Prometheus-formatted metrics
        """
        metrics = []
        
        # Total messages
        metrics.append(
            MetricsView.format_metric(
                'mta_queue_messages_total',
                'gauge',
                'Total number of messages in queue',
                [(None, stats.get('total', 0))]
            )
        )
        
        # Messages by status
        if 'by_status' in stats:
            values = [(
                {'status': status},
                count
            ) for status, count in stats['by_status'].items()]
            
            metrics.append(
                MetricsView.format_metric(
                    'mta_queue_messages_by_status',
                    'gauge',
                    'Number of messages by status',
                    values
                )
            )
        
        # Pending messages
        metrics.append(
            MetricsView.format_metric(
                'mta_queue_pending',
                'gauge',
                'Number of pending messages',
                [(None, stats.get('pending', 0))]
            )
        )
        
        # Completed messages
        metrics.append(
            MetricsView.format_metric(
                'mta_queue_completed',
                'gauge',
                'Number of completed messages (delivered + bounced)',
                [(None, stats.get('completed', 0))]
            )
        )
        
        return '\n\n'.join(metrics) + '\n'
    
    @staticmethod
    def rate_limit_metrics(stats: Dict[str, Any]) -> str:
        """
        Format rate limit statistics as Prometheus metrics
        
        Args:
            stats: Rate limit statistics dictionary
            
        Returns:
            Prometheus-formatted metrics
        """
        metrics = []
        
        # Total rate limits
        metrics.append(
            MetricsView.format_metric(
                'mta_rate_limits_total',
                'gauge',
                'Total number of active rate limits',
                [(None, stats.get('total_limits', 0))]
            )
        )
        
        # Rate limits by type
        if 'by_type' in stats:
            values = [(
                {'type': limit_type},
                data['count']
            ) for limit_type, data in stats['by_type'].items()]
            
            metrics.append(
                MetricsView.format_metric(
                    'mta_rate_limits_by_type',
                    'gauge',
                    'Number of rate limits by type',
                    values
                )
            )
            
            # Total requests by type
            values = [(
                {'type': limit_type},
                data['total_requests']
            ) for limit_type, data in stats['by_type'].items()]
            
            metrics.append(
                MetricsView.format_metric(
                    'mta_rate_limit_requests_total',
                    'counter',
                    'Total requests checked against rate limits',
                    values
                )
            )
            
            # Rejected requests by type
            values = [(
                {'type': limit_type},
                data['rejected_requests']
            ) for limit_type, data in stats['by_type'].items()]
            
            metrics.append(
                MetricsView.format_metric(
                    'mta_rate_limit_rejections_total',
                    'counter',
                    'Total requests rejected by rate limits',
                    values
                )
            )
        
        return '\n\n'.join(metrics) + '\n'
    
    @staticmethod
    def user_metrics(user_count: int, active_users: int = None) -> str:
        """
        Format user statistics as Prometheus metrics
        
        Args:
            user_count: Total number of users
            active_users: Number of active users (optional)
            
        Returns:
            Prometheus-formatted metrics
        """
        metrics = []
        
        # Total users
        metrics.append(
            MetricsView.format_metric(
                'mta_users_total',
                'gauge',
                'Total number of users',
                [(None, user_count)]
            )
        )
        
        # Active users
        if active_users is not None:
            metrics.append(
                MetricsView.format_metric(
                    'mta_users_active',
                    'gauge',
                    'Number of active users',
                    [(None, active_users)]
                )
            )
        
        return '\n\n'.join(metrics) + '\n'
    
    @staticmethod
    def policy_metrics(blacklist_count: int, whitelist_count: int,
                      greylist_count: int = 0) -> str:
        """
        Format policy statistics as Prometheus metrics
        
        Args:
            blacklist_count: Number of blacklisted items
            whitelist_count: Number of whitelisted items
            greylist_count: Number of greylisted entries
            
        Returns:
            Prometheus-formatted metrics
        """
        metrics = []
        
        # Blacklist
        metrics.append(
            MetricsView.format_metric(
                'mta_blacklist_entries',
                'gauge',
                'Number of blacklisted entries',
                [(None, blacklist_count)]
            )
        )
        
        # Whitelist
        metrics.append(
            MetricsView.format_metric(
                'mta_whitelist_entries',
                'gauge',
                'Number of whitelisted entries',
                [(None, whitelist_count)]
            )
        )
        
        # Greylist
        if greylist_count > 0:
            metrics.append(
                MetricsView.format_metric(
                    'mta_greylist_entries',
                    'gauge',
                    'Number of active greylist entries',
                    [(None, greylist_count)]
                )
            )
        
        return '\n\n'.join(metrics) + '\n'
    
    @staticmethod
    def combine_metrics(*metric_strings: str) -> str:
        """
        Combine multiple metric strings
        
        Args:
            *metric_strings: Variable number of metric strings
            
        Returns:
            Combined metrics string
        """
        return '\n'.join(m.strip() for m in metric_strings if m) + '\n'
