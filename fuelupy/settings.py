from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ─────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ── Applications ──────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fuelupy.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fuelupy.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'  # San Jose, CA pilot
USE_I18N = True
USE_TZ = True

# ── Static & Media ────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── FuelUp — External API Keys ───────────────────────────────────────────────
ANTHROPIC_API_KEY     = os.getenv('ANTHROPIC_API_KEY')
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')

# ── FuelUp — Web Push (VAPID) ────────────────────────────────────────────────
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')
VAPID_PUBLIC_KEY  = os.getenv('VAPID_PUBLIC_KEY')
VAPID_CONTACT     = os.getenv('VAPID_CONTACT', 'mailto:purvi@dietsandlife.com')

# ── FuelUp — App Config ───────────────────────────────────────────────────────
FUELUP_DB_PATH     = BASE_DIR / 'fuelup.db'
FUELUP_LAUNCH_DATE = '2026-06-16'
FUELUP_DISCLAIMER  = 'FuelUp provides educational food guidance — not medical nutrition therapy.'
