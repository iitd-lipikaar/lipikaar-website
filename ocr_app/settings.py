"""
Start Redis
    sudo service redis-server start
Check Redis
    redis-cli ping
Start Celery
    celery -A ocr.celery worker -Q re_run_ocr,ocr_for_service,new_uploads -Ofair --pool=solo -l INFO -f celery_logs.log
Start Django Server
    python3 manage.py startup && python3 manage.py runserver
"""

from pathlib import Path
from datetime import timedelta
from os.path import join
from decouple import config


BASE_DIR = Path(__file__).resolve().parent.parent

#region Load env vars
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')
PAGE_LIMIT_PER_USER_PER_DAY = config('PAGE_LIMIT_PER_USER_PER_DAY', default=10, cast=int)
NEW_UPLOAD_QUEUE_SIZE_LIMIT = config('NEW_UPLOAD_QUEUE_SIZE_LIMIT', default=10, cast=int)
BACKEND_BASE_URL = config('BACKEND_BASE_URL')
GET_MULTIPLE_UPLOADS_LIMIT = config('GET_MULTIPLE_UPLOADS_LIMIT', default=5, cast=int)
CAN_DELETE_MULTIPLE_UPLOADS_IN_SINGLE_REQUEST = config('CAN_DELETE_MULTIPLE_UPLOADS_IN_SINGLE_REQUEST', default=False, cast=bool)
CS__ALLOWED_HOSTS = config('CS__ALLOWED_HOSTS')
CS__CORS_ORIGIN_WHITELIST = config('CS__CORS_ORIGIN_WHITELIST')
DOCUMENT_PARSERS_API_PROVIDER_URL = config('DOCUMENT_PARSERS_API_PROVIDER_URL')
TEXT_RECOGNIZERS_API_PROVIDER_URL = config('TEXT_RECOGNIZERS_API_PROVIDER_URL')
DJANGO_TIME_ZONE = config('DJANGO_TIME_ZONE')
DJANGO_LANGUAGE_CODE = config('DJANGO_LANGUAGE_CODE')
BACKEND_VERSION = config('BACKEND_VERSION')
FRONTEND_VERSION = config('FRONTEND_VERSION')
SERVICE_API_KEY = config('SERVICE_API_KEY')
#endregion

NEW_OCR_ACCEPTED_FILE_EXTENSIONS = [".pdf", ".jpg", ".jpeg"]

# region AllowedHosts and CORS Settings
ALLOWED_HOSTS=["*"] if DEBUG else CS__ALLOWED_HOSTS.split(',')

CORS_ORIGIN_ALLOW_ALL = DEBUG
CORS_ORIGIN_WHITELIST = CS__CORS_ORIGIN_WHITELIST.split(',')
#endregion

ROOT_URLCONF = 'ocr_app.urls'
WSGI_APPLICATION = 'ocr_app.wsgi.application'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_object_actions',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'ocr',
    'frontend_core',
    'django_celery_results',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [join(BASE_DIR, "build"), join(BASE_DIR, "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

#region Database Settings
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
}
#endregion

#region Authentication Settings
AUTH_USER_MODEL = 'ocr.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
#endregion

#region Language and Time Zone Settings
LANGUAGE_CODE = DJANGO_LANGUAGE_CODE

TIME_ZONE = DJANGO_TIME_ZONE

USE_I18N = True

USE_TZ = True
#endregion

#region Static, Media, and Cache Settings
STATIC_URL = '/static/'
STATIC_ROOT = join(BASE_DIR, 'static')
STATICFILES_DIRS = (
    join(BASE_DIR, "build"),
    join(BASE_DIR, "build/static"),
)
MEDIA_URL= "/media/"
MEDIA_ROOT = join(BASE_DIR, "media")
CACHE_ROOT = join(BASE_DIR, "cache")
#endregion

#region DRF Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
#endregion

#region DRF Simple JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=15) if DEBUG else timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=90),

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',
}
#endregion

#region Celery Settings
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
#endregion

#region CRON Jobs
CRONJOBS = [
    ('*/14 * * * *', 'ocr.cron.mark_old_unprocessed_uploads_as_errored')
]
#endregion
