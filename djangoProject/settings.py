"""
Django settings for djangoProject project.

Generated by 'django-admin startproject' using Django 4.2.14.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
import uuid
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "django-insecure-c@&8cjq7p*g*#!)3(nj(9n%hsd(&z^bnfr7vjpa-+%d+11l42s"
)

# CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DJANGO_DEBUG", "1").lower() in ("1", "yes", "true")  # По умолчанию True

ALLOWED_HOSTS = ["*"]

INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "tasks",
    "user",
    "django_filters",
    "ckeditor",
    "ckeditor_uploader",
]

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]

AUTH_USER_MODEL = "user.User"
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

ROOT_URLCONF = "djangoProject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "djangoProject.extra_processors.get_random_icon",
                "djangoProject.extra_processors.get_current_page",
            ],
        },
    },
]

WSGI_APPLICATION = "djangoProject.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

if os.getenv("DJANGO_DATABASE_ENGINE") == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "HOST": os.getenv("DJANGO_DATABASE_HOST"),
            "PORT": 5432,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ==============================  CACHE ==================================

if os.getenv("DJANGO_REDIS_CACHE_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.getenv("DJANGO_REDIS_CACHE_URL"),

        }

    }

    # Password validation
    # https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"

# Для сбора статики:
if os.getenv("DJANGO_COLLECT_STATIC", "0").lower() in ("1", "yes", "true"):
    STATIC_ROOT = BASE_DIR / "static"
else:
    STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
# MEDIA_URL = '/media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "user/login/"


# ==============================  CKEDITOR ==================================


def get_filename(file_name: str, request) -> str:
    return str(uuid.uuid4()) + "-" + file_name


CKEDITOR_UPLOAD_PATH = "uploads/"

CKEDITOR_FILENAME_GENERATOR = "djangoProject.settings.get_filename"

CKEDITOR_CONFIGS = {
    'default': {
        'height': 150,
        # 'skin': 'office2013',
        'toolbar_Basic': [
            ['Source', '-', 'Bold', 'Italic']
        ],
        'toolbar_YourCustomToolbarConfig': [
            {'name': 'styles', 'items': ['Font', 'FontSize', 'Styles', ]},
            {'name': 'basicstyles',
             'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', ]},

            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'basicstyles',
             'items': ['RemoveFormat', ]},
            {'name': 'paragraph',
             'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-',
                       'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-', ]},
            {'name': 'links', 'items': ['Image', 'Link', 'Unlink']},
            {'name': 'insert',
             'items': ['Flash', 'Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'PageBreak', ]},

            # '/',  # put this to force next toolbar on new line
            # {'name': 'basicstyles',
            #  'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', ]},
            # {'name': 'basicstyles',
            #  'items': ['RemoveFormat', ]},
            # '/',

        ],
        'toolbar': 'YourCustomToolbarConfig',  # put selected toolbar config here
        # 'toolbarGroups': [{ 'name': 'document', 'groups': [ 'mode', 'document', 'doctools' ] }],
        # 'height': 291,
        # 'width': '100%',
        # 'filebrowserWindowHeight': 725,
        # 'filebrowserWindowWidth': 940,
        # 'toolbarCanCollapse': True,
        # 'mathJaxLib': '//cdn.mathjax.org/mathjax/2.2-latest/MathJax.js?config=TeX-AMS_HTML',
        'tabSpaces': 4,
        # 'filebrowserUploadUrl': '/ckeditor/upload/',
        # 'filebrowserBrowseUrl': '/ckeditor/browse/',
        'extraPlugins': ','.join([
            'uploadimage',  # the upload image feature
            # your extra plugins here
            # 'div',
            'autolink',
            # 'autoembed',
            # 'embedsemantic',
            # 'autogrow',
            # 'devtools',
            # 'widget',
            # 'lineutils',
            # 'clipboard',
            # 'dialog',
            # 'dialogui',
            # 'elementspath'
        ]),
        'filebrowserUploadUrl': '/ckeditor/upload/',
        'filebrowserBrowseUrl': '/ckeditor/browse/',
        'imageUploadUrl': '/ckeditor/upload/',
    },
    'minimal': {
        'height': 150,
        # 'skin': 'office2013',
        'toolbar_Basic': [
            ['Source', '-', 'Bold', 'Italic']
        ],
        'toolbar_YourCustomToolbarConfig': [
            {'name': 'styles', 'items': ['Font', 'FontSize', 'Styles', ]},

            {'name': 'basicstyles',
             'items': ['Bold', 'Italic', 'Underline', 'Strike', 'TextColor', 'BGColor', 'Subscript', 'Superscript',
                       '-', ]},

            {'name': 'basicstyles', 'items': ['RemoveFormat', ]},
            {'name': 'links', 'items': ['Image', 'Link', 'Unlink']},

            # '/',  # put this to force next toolbar on new line

            '/',

        ],
        'toolbar': 'YourCustomToolbarConfig',  # put selected toolbar config here
        # 'toolbarGroups': [{ 'name': 'document', 'groups': [ 'mode', 'document', 'doctools' ] }],
        # 'height': 291,
        # 'width': '100%',
        # 'filebrowserWindowHeight': 725,
        # 'filebrowserWindowWidth': 940,
        # 'toolbarCanCollapse': True,
        # 'mathJaxLib': '//cdn.mathjax.org/mathjax/2.2-latest/MathJax.js?config=TeX-AMS_HTML',
        'tabSpaces': 4,
        # 'filebrowserUploadUrl': '/ckeditor/upload/',
        # 'filebrowserBrowseUrl': '/ckeditor/browse/',
        'extraPlugins': ','.join([
            'uploadimage',  # the upload image feature
            # your extra plugins here
            # 'div',
            'autolink',
            # 'autoembed',
            # 'embedsemantic',
            # 'autogrow',
            # 'devtools',
            # 'widget',
            # 'lineutils',
            # 'clipboard',
            # 'dialog',
            # 'dialogui',
            # 'elementspath'
        ]),
        'filebrowserUploadUrl': '/ckeditor/upload/',
        'filebrowserBrowseUrl': '/ckeditor/browse/',
        'imageUploadUrl': '/ckeditor/upload/',
    }
}
