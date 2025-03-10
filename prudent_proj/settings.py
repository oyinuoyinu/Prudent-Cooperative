"""
Django settings for prudent_proj project.

Generated by 'django-admin startproject' using Django 5.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
from decouple import config
import dj_database_url


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent



# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = "django-insecure-^6rvrhs5-53cs$%(mg(8kk7jqsl!%q-m%_))n318@w_&$zrf++"

# # SECURITY WARNING: don't run with debug turned on in production!

# DEBUG = True
# ALLOWED_HOSTS = []
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-^6rvrhs5-53cs$%(mg(8kk7jqsl!%q-m%_))n318@w_&$zrf++')
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = ['*.onrender.com',]

# Application definition

INSTALLED_APPS = [
    'django_daisy',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    'django.contrib.humanize',
    "django.contrib.staticfiles",
    # "django.contrib.sites",
    "accounts.apps.AccountsConfig",
    "members.apps.MembersConfig",  # Use the custom app config
    "savings.apps.SavingsConfig",
    "loans.apps.LoansConfig",
    "mono.apps.MonoConfig",
    # "apis.apps.ApisConfig",
    'crispy_forms',
    'crispy_bootstrap5',
    "herald",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "prudent_proj.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'accounts.context_processors.get_member',
                'accounts.context_processors.get_user_profile',
                'accounts.context_processors.get_customer',
            ],
        },
    },
]

WSGI_APPLICATION = "prudent_proj.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }






# Database
DATABASE_URL = os.getenv('DATABASE_URL')
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),  # Fallback to SQLite
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Ensure the static directory exists
os.makedirs(os.path.join(BASE_DIR, 'static'), exist_ok=True)


# Configure whitenoise for better static file handling
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'  # Changed from CompressedManifestStaticFilesStorage

# Add these lines for Render deployment
if not DEBUG:
    STATIC_HOST = os.environ.get('STATIC_HOST', '')
    STATIC_URL = STATIC_HOST + '/static/'
    WHITENOISE_ROOT = os.path.join(BASE_DIR, 'staticfiles', 'root')



# Security
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Lagos"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

# STATIC_URL = '/static/'
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, 'static'),
# ]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = 'accounts.User'


# Flash messages
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}

# Crispy Forms Settings
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

#Email settings
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "jamezslim90@gmail.com"
    EMAIL_HOST_PASSWORD = "ugsciuxxbyinkuiu"  # Replace this with your new App Password
    EMAIL_TIMEOUT = 5  # Reduced timeout for faster error detection

DEFAULT_FROM_EMAIL = 'MMS WoF HoF <jamezslim90@gmail.com>'

# For development, store emails in the console
if DEBUG:
    EMAIL_FILE_PATH = BASE_DIR / 'sent_emails'


# Paystack Settings

PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY')
MEMBERSHIP_FEE = 2000

# Mono Settings

# MONO_SECRET_KEY ='test_sk_v0569w0snjimze2ec8rn'
# MONO_PUBLIC_KEY ='test_pk_bvq5hk0dhkazuftbt2hu'

MONO_SECRET_KEY = 'live_sk_dgjv2brhde13rlavqrrg'
MONO_PUBLIC_KEY = 'live_pk_dfaf4zx7zf2x8dzfx731'

# Content Security Policy Settings
CSP_DEFAULT_SRC = (
    "'self'",
    "https://*.paystack.co",
    "https://*.paystack.com",
    "https://*.mono.co",
    "https://*.withmono.com",
)

CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
    "https://*.paystack.co",
    "https://*.paystack.com",
    "https://js.paystack.co",
    "https://checkout.paystack.com",
    "https://mono.co",
    "https://*.mono.co",
    "https://*.withmono.com",
    "https://connect.withmono.com",
)

CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    "https://*.mono.co",
    "https://*.withmono.com",
)

CSP_FRAME_SRC = (
    "'self'",
    "https://*.paystack.co",
    "https://*.paystack.com",
)

CSP_CONNECT_SRC = (
    "'self'",
    "https://*.paystack.co",
    "https://*.paystack.com",
)

CSP_IMG_SRC = (
    "'self'",
    "data:",
    "https://*.paystack.co",
    "https://*.paystack.com",
    "https://connect.withmono.com",
    "https://*.mono.co",
    "https://*.withmono.com",
)


# JAZZMIN_SETTINGS = {
#     # title of the window (Will default to current_admin_site.site_title if absent or None)
#     "site_title": "Prudent Women Admin",

#     # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
#     "site_header": "Prudent Women Admin",

#     # Title on the brand (19 chars max) (defaults to current_admin_site.site_header if absent or None)
#     "site_brand": "Prudent Women Admin",

#     # Logo to use for your site, must be present in static files, used for brand on top left
#     "site_logo": "static/images/logo.jpeg",

#     # Logo to use for your site, must be present in static files, used for login form logo (defaults to site_logo)
#     "login_logo": None,

#     # Logo to use for login form in dark themes (defaults to login_logo)
#     "login_logo_dark": None,

#     # CSS classes that are applied to the logo above
#     "site_logo_classes": "img-circle",

#     # Relative path to a favicon for your site, will default to site_logo if absent (ideally 32x32 px)
#     "site_icon": None,

#     # Welcome text on the login screen
#     "welcome_sign": "Welcome to the library",

#     # Copyright on the footer
#     "copyright": "Acme Library Ltd",

#     # List of model admins to search from the search bar, search bar omitted if excluded
#     # If you want to use a single search field you dont need to use a list, you can use a simple string
#     "search_model": ["auth.User", "auth.Group"],

#     # Field name on user model that contains avatar ImageField/URLField/Charfield or a callable that receives the user
#     "user_avatar": None,

#     ############
#     # Top Menu #
#     ############

#     # Links to put along the top menu
#     "topmenu_links": [

#         # Url that gets reversed (Permissions can be added)
#         {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},

#         # external url that opens in a new window (Permissions can be added)
#         {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},

#         # model admin to link to (Permissions checked against model)
#         {"model": "auth.User"},

#         # App with dropdown menu to all its models pages (Permissions checked against models)
#         {"app": "books"},
#     ],

#     #############
#     # User Menu #
#     #############

#     # Additional links to include in the user menu on the top right ("app" url type is not allowed)
#     "usermenu_links": [
#         {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},
#         {"model": "auth.user"}
#     ],

#     #############
#     # Side Menu #
#     #############

#     # Whether to display the side menu
#     "show_sidebar": True,

#     # Whether to aut expand the menu
#     "navigation_expanded": True,

#     # Hide these apps when generating side menu e.g (auth)
#     "hide_apps": [],

#     # Hide these models when generating side menu (e.g auth.user)
#     "hide_models": [],

#     # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps/models)
#     "order_with_respect_to": ["auth", "books", "books.author", "books.book"],

#     # Custom links to append to app groups, keyed on app name
#     "custom_links": {
#         "books": [{
#             "name": "Make Messages",
#             "url": "make_messages",
#             "icon": "fas fa-comments",
#             "permissions": ["books.view_book"]
#         }]
#     },

#     # Custom icons for side menu apps/models See https://fontawesome.com/icons?d=gallery&m=free&v=5.0.0,5.0.1,5.0.10,5.0.11,5.0.12,5.0.13,5.0.2,5.0.3,5.0.4,5.0.5,5.0.6,5.0.7,5.0.8,5.0.9,5.1.0,5.1.1,5.2.0,5.3.0,5.3.1,5.4.0,5.4.1,5.4.2,5.13.0,5.12.0,5.11.2,5.11.1,5.10.0,5.9.0,5.8.2,5.8.1,5.7.2,5.7.1,5.7.0,5.6.3,5.5.0,5.4.2
#     # for the full list of 5.13.0 free icon classes
#     "icons": {
#         "auth": "fas fa-users-cog",
#         "auth.user": "fas fa-user",
#         "auth.Group": "fas fa-users",
#     },
#     # Icons that are used when one is not manually specified
#     "default_icon_parents": "fas fa-chevron-circle-right",
#     "default_icon_children": "fas fa-circle",

#     #################
#     # Related Modal #
#     #################
#     # Use modals instead of popups
#     "related_modal_active": False,

#     #############
#     # UI Tweaks #
#     #############
#     # Relative paths to custom CSS/JS scripts (must be present in static files)
#     "custom_css": None,
#     "custom_js": None,
#     # Whether to link font from fonts.googleapis.com (use custom_css to supply font otherwise)
#     "use_google_fonts_cdn": True,
#     # Whether to show the UI customizer on the sidebar
#     "show_ui_builder": False,

#     ###############
#     # Change view #
#     ###############
#     # Render out the change view as a single form, or in tabs, current options are
#     # - single
#     # - horizontal_tabs (default)
#     # - vertical_tabs
#     # - collapsible
#     # - carousel
#     "changeform_format": "horizontal_tabs",
#     # override change forms on a per modeladmin basis
#     "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},
#     # Add a language dropdown into the admin
#     "language_chooser": True,
# }




DAISY_SETTINGS = {
    'SITE_TITLE': 'Prudent Women Admin',  # The title of the site
    'SITE_HEADER': 'Administration',  # Header text displayed in the admin panel
    'INDEX_TITLE': 'Hi, welcome to your dashboard',  # The title for the index page of dashboard
    'SITE_LOGO': '/static/admin/img/daisyui-logomark.svg',  # Path to the logo image displayed in the sidebar
    'EXTRA_STYLES': [],  # List of extra stylesheets to be loaded in base.html (optional)
    'EXTRA_SCRIPTS': [],  # List of extra script URLs to be loaded in base.html (optional)
    'LOAD_FULL_STYLES': False,  # If True, loads full DaisyUI components in the admin (useful if you have custom template overrides)
    'SHOW_CHANGELIST_FILTER': False,  # If True, the filter sidebar will open by default on changelist views
    'DONT_SUPPORT_ME': False, # Hide github link in sidebar footer
    'SIDEBAR_FOOTNOTE': '', # add footnote to sidebar
    'APPS_REORDER': {
        # Custom configurations for third-party apps that can't be modified directly in their `apps.py`
        'auth': {
            'icon': 'fa-solid fa-person-military-pointing',  # FontAwesome icon for the 'auth' app
            'name': 'Authentication',  # Custom name for the 'auth' app
            'hide': False,  # Whether to hide the 'auth' app from the sidebar (set to True to hide)
            'divider_title': "Auth",  # Divider title for the 'auth' section
        },
        'social_django': {
            'icon': 'fa-solid fa-users-gear',  # Custom FontAwesome icon for the 'social_django' app
        },
    },
}