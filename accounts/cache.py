from django.core.cache import cache
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile

class ProfileCache:
    CACHE_TTL = getattr(settings, 'PROFILE_CACHE_TTL', 3600)  # 1 hour default
    
    @staticmethod
    def get_cache_key(user_id):
        return f'user_profile_{user_id}'
    
    @classmethod
    def get_profile(cls, user_id):
        """Get user profile from cache or database"""
        cache_key = cls.get_cache_key(user_id)
        profile = cache.get(cache_key)
        
        if profile is None:
            try:
                profile = UserProfile.objects.select_related('user').get(user_id=user_id)
                cache.set(cache_key, profile, cls.CACHE_TTL)
            except UserProfile.DoesNotExist:
                return None
        
        return profile
    
    @classmethod
    def invalidate_profile_cache(cls, user_id):
        """Remove profile from cache"""
        cache_key = cls.get_cache_key(user_id)
        cache.delete(cache_key)

# Signal to invalidate cache when profile is updated
@receiver(post_save, sender=UserProfile)
def invalidate_profile_cache(sender, instance, **kwargs):
    ProfileCache.invalidate_profile_cache(instance.user_id)

# Database query optimization mixin
class OptimizedQuerySetMixin:
    def get_queryset(self):
        return super().get_queryset().select_related(
            'user',
            'user__userprofile'
        ).prefetch_related(
            'user__groups',
            'user__user_permissions'
        )
