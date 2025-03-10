from django.shortcuts import redirect
from django.urls import resolve
from django.urls.base import resolve, Resolver404
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from ..utils import detect_user_role, get_allowed_urls_for_role

class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware for static, media, and admin URLs
        if (request.path.startswith((settings.STATIC_URL, settings.MEDIA_URL, '/admin/'))):
            return self.get_response(request)

        try:
            current_url = resolve(request.path_info).url_name
            if not current_url:
                return self.get_response(request)

            # Handle unauthenticated users
            if not request.user.is_authenticated:
                # Allow access to public URLs
                if current_url in get_allowed_urls_for_role(None):
                    return self.get_response(request)
                # Redirect to login for protected URLs
                return redirect_to_login(request.path)

            # For authenticated users, check role-based access
            allowed_urls = get_allowed_urls_for_role(request.user.role)
            if current_url not in allowed_urls:
                # Get correct dashboard based on role
                target_url = detect_user_role(request.user)
                if current_url != target_url.split(':')[1]:  # Prevent redirect loops
                    return redirect(target_url)

        except Resolver404:
            pass

        return self.get_response(request)
