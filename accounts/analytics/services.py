from django.db.models import Count, Avg, F, ExpressionWrapper, fields
from django.db.models.functions import TruncDate, ExtractHour
from django.utils import timezone
from datetime import timedelta
from .models import UserActivity, LoginAttempt, UserMetrics

class UserAnalyticsService:
    @staticmethod
    def get_login_patterns(days=30):
        """Analyze login patterns over time"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        return LoginAttempt.objects.filter(
            timestamp__range=(start_date, end_date),
            success=True
        ).annotate(
            date=TruncDate('timestamp'),
            hour=ExtractHour('timestamp')
        ).values('date', 'hour').annotate(
            count=Count('id')
        ).order_by('date', 'hour')
    
    @staticmethod
    def get_user_engagement_metrics(user):
        """Get user engagement metrics"""
        now = timezone.now()
        activities = UserActivity.objects.filter(
            user=user,
            timestamp__gte=now - timedelta(days=30)
        )
        
        return {
            'total_actions': activities.count(),
            'unique_actions': activities.values('action').distinct().count(),
            'most_common_action': activities.values('action').annotate(
                count=Count('id')
            ).order_by('-count').first(),
            'last_active': activities.latest('timestamp').timestamp if activities.exists() else None,
        }
    
    @staticmethod
    def get_security_metrics(user):
        """Get security-related metrics"""
        login_attempts = LoginAttempt.objects.filter(
            email=user.email,
            timestamp__gte=timezone.now() - timedelta(days=30)
        )
        
        return {
            'failed_attempts': login_attempts.filter(success=False).count(),
            'success_rate': (
                login_attempts.filter(success=True).count() /
                login_attempts.count() * 100 if login_attempts.exists() else 0
            ),
            'unique_ips': login_attempts.values('ip_address').distinct().count(),
        }
    
    @staticmethod
    def track_activity(user, action, ip_address=None, device_info=None):
        """Track user activity"""
        UserActivity.objects.create(
            user=user,
            action=action,
            ip_address=ip_address,
            device_info=device_info or {}
        )
        
    @classmethod
    def generate_user_report(cls, user):
        """Generate comprehensive user report"""
        metrics = UserMetrics.objects.get_or_create(user=user)[0]
        engagement = cls.get_user_engagement_metrics(user)
        security = cls.get_security_metrics(user)
        
        metrics.calculate_profile_completion()
        
        return {
            'user_id': user.id,
            'email': user.email,
            'profile_completion': metrics.profile_completion,
            'account_age_days': metrics.account_age_days,
            'engagement_metrics': engagement,
            'security_metrics': security,
        }
