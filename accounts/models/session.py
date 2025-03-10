from django.db import models
from django.conf import settings
from django.utils import timezone

class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255)
    last_activity = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    device_type = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-last_activity']

    def __str__(self):
        return f"{self.user.email} - {self.device_type} - {self.last_activity}"
