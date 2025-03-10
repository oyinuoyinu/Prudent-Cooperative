from django.utils import timezone
from accounts.models.session import UserSession
from user_agents import parse

class SessionTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated:
            # Get or create session
            session_key = request.session.session_key
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            ip_address = self.get_client_ip(request)
            
            # Parse user agent for device info
            ua_string = parse(user_agent)
            device_type = self.get_device_type(ua_string)
            
            # Update or create session record
            UserSession.objects.update_or_create(
                user=request.user,
                session_key=session_key,
                defaults={
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'last_activity': timezone.now(),
                    'device_type': device_type,
                }
            )
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_device_type(self, user_agent):
        if user_agent.is_mobile:
            return 'Mobile'
        elif user_agent.is_tablet:
            return 'Tablet'
        elif user_agent.is_pc:
            return 'Desktop'
        return 'Other'
