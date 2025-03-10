from django.db import models
from django.conf import settings
from django.utils import timezone

class UserActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # e.g., 'login', 'logout', 'profile_update'
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True)
    device_info = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['timestamp']),
        ]

class LoginAttempt(models.Model):
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['email', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
        ]

class UserMetrics(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_login_attempt = models.DateTimeField(null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    successful_logins = models.PositiveIntegerField(default=0)
    profile_completion = models.FloatField(default=0)  # percentage
    last_password_change = models.DateTimeField(null=True)
    account_age_days = models.PositiveIntegerField(default=0)
    
    def calculate_profile_completion(self):
        """Calculate profile completion percentage"""
        profile = self.user.userprofile
        fields = [
            profile.profile_picture,
            profile.phone_number,
            profile.address,
            profile.country,
            profile.state,
            profile.city
        ]
        completed = sum(1 for field in fields if field)
        self.profile_completion = (completed / len(fields)) * 100
        self.save()
