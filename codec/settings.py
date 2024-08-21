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

# Allow localhost for local development
APP_NAME = os.environ.get("FLY_APP_NAME")  # Set in production on fly.io
if APP_NAME:
    DEBUG = False
    FRONTEND_URL = f"https://{APP_NAME}.fly.dev"
    ALLOWED_HOSTS = [f"{APP_NAME}.fly.dev"]
else:
    DEBUG = True
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

if not DEBUG:
    MIDDLEWARE += ("apitally.django_rest_framework.ApitallyMiddleware",)

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
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "codec",
            "USER": "codec",
            "PASSWORD": "codec",
            "HOST": "",
            "PORT": "",
        }
    }
else:
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
    "DEFAULT_THROTTLE_RATES": {"anon": "2000/day", "user": "10000000/day"},
}

# Celery
CELERY_BROKER_URL = env.str("REDIS_URL", "redis://localhost:6379/")
CELERY_BEAT_SCHEDULE = {
    "crawl-feeds-every-3-hours": {
        "task": "web.tasks.crawler_tasks.crawl_top_feeds",
        "schedule": crontab(minute=0, hour="*/3"),
    },
    "crawl-itunes-weekly": {
        "task": "web.tasks.crawler_tasks.crawl_itunes",
        "schedule": crontab(minute=0, hour=10, day_of_week="tuesday"),  # Tues 3am PST
    },
    "calculate-feed-popularity-every-hour": {
        "task": "web.tasks.ranker_tasks.rank_all_feeds_popularity",
        "schedule": crontab(minute=0, hour="*/1"),
    },
    "update-active-users-daily": {
        "task": "web.tasks.update_active_users",
        "schedule": crontab(hour=0, minute=0),
    },
}
CELERY_RESULT_EXTENDED = True

# Cloudflare R2 Storage Bucket
R2_URL = env("R2_URL")
R2_ACCESS_KEY = env("R2_ACCESS_KEY")
R2_SECRET_KEY = env("R2_SECRET_KEY")
R2_BUCKET_NAME = "codec-bucket"  # env("R2_BUCKET_NAME")
R2_BUCKET_URL = env("R2_BUCKET_URL")

# Service API Keys
ASSEMBLYAI_API_KEY = env("ASSEMBLYAI_API_KEY")
RESEND_API_KEY = env("RESEND_API_KEY")
SCRAPING_FISH_API_KEY = env("SCRAPING_FISH_API_KEY")
COHERE_API_KEY = env("COHERE_API_KEY")
SENTRY_DSN = env("SENTRY_DSN")
APITALLY_CLIENT_ID = env("APITALLY_CLIENT_ID")
BRAINTRUST_API_KEY = env("BRAINTRUST_API_KEY")
OPENAI_API_KEY = env("OPENAI_API_KEY")
LANGSMITH_API_KEY = env("LANGSMITH_API_KEY")
LANGCHAIN_TRACING_V2 = True
LOGSNAG_API_KEY = env("LOGSNAG_API_KEY")
GCLOUD_API_KEY = env("GCLOUD_API_KEY")

if not DEBUG:
    # Sentry
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment="production",
        send_default_pii=True,
    )

    # Apitally
    APITALLY_MIDDLEWARE = {
        "client_id": APITALLY_CLIENT_ID,
        "env": "prod",
        "identify_consumer_callback": "web.lib.identify_consumer.identify_consumer",
    }
