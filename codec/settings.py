from pathlib import Path
import os
import environ
from celery.schedules import crontab
import sentry_sdk

env = environ.Env(  # <-- Updated!
    # set casting, default value
    DEBUG=(bool, False),
)


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
environ.Env.read_env(BASE_DIR / ".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

# Allow localhost for local development
APP_NAME = os.environ.get("FLY_APP_NAME")
if APP_NAME:
    FRONTEND_URL = f"https://{APP_NAME}.fly.dev"
    ALLOWED_HOSTS = [f"{APP_NAME}.fly.dev"]
else:
    FRONTEND_URL = "http://localhost:8000"
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

CSRF_TRUSTED_ORIGINS = ["https://*.fly.dev"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.postgres",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "django_celery_results",
    "web.apps.WebConfig",
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

ROOT_URLCONF = "codec.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "codec.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    # read os.environ['DATABASE_URL']
    "default": env.db()
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "100/day", "user": "10000000/day"},
}

# Celery
CELERY_BROKER_URL = env.str("REDIS_URL", "redis://localhost:6379/")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", "django-db")
CELERY_BEAT_SCHEDULE = {
    "crawl-feeds-every-3-hours": {
        "task": "web.tasks.crawler_tasks.crawl_top_feeds",
        "schedule": crontab(minute=0, hour="*/3"),
    },
    "crawl-itunes-weekly": {
        "task": "web.tasks.crawler_tasks.crawl_itunes",
        "schedule": crontab(minute=0, hour=10, day_of_week="tuesday"),  # Tues 3am PST
    },
    "rank-new-clips-hourly": {
        "task": "web.tasks.ranker_tasks.rank_new_clips",
        "schedule": crontab(minute=30, hour="*"),
    },
    "re-rank-every-10-minutes": {
        "task": "web.tasks.ranker_tasks.re_rank_using_views",
        "schedule": crontab(minute="*/10"),
    },
}
CELERY_RESULT_EXTENDED = True

# Cloudflare R2 Storage Bucket
R2_URL = env("R2_URL")
R2_ACCESS_KEY = env("R2_ACCESS_KEY")
R2_SECRET_KEY = env("R2_SECRET_KEY")
R2_BUCKET_NAME = env("R2_BUCKET_NAME")
R2_BUCKET_URL = env("R2_BUCKET_URL")

# Service API Keys
ASSEMBLYAI_API_KEY = env("ASSEMBLYAI_API_KEY")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
HELICONE_API_KEY = env("HELICONE_API_KEY")
RESEND_API_KEY = env("RESEND_API_KEY")
SCRAPING_FISH_API_KEY = env("SCRAPING_FISH_API_KEY")
COHERE_API_KEY = env("COHERE_API_KEY")
SENTRY_DSN = env("SENTRY_DSN")

# Sentry
sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    environment="production" if not DEBUG else "development",
)
