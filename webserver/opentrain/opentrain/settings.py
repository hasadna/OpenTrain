"""
Django settings for opentrain project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DATA_DIR = os.path.join(BASE_DIR,'tmp_data')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'sjwt&eblxp_hkl*u9=p3xg2)xh)e_ar6sy_^i(n+7pfec%24oz'

# SECURITY WARNING: don't run with debug turned on in production!

DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrap3_datetime', 
    'gtfs',
    'common',
    'reports',
    'analysis',
    'algorithm',
    'django_extensions',
    'redis_intf',
    'statici18n',
    'south',
    'ot_api',
    'traindata',
    'client',
    'timetable'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'common.middleware.OpenTrainMiddleware',
)

ROOT_URLCONF = 'opentrain.urls'

WSGI_APPLICATION = 'opentrain.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

#if not os.path.exists('/tmp/opentrain'):
#    os.mkdir('/tmp/opentrain')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'opentrain',                      
        'USER': 'opentrain',
        'PASSWORD': 'opentrain',
        'HOST': 'localhost'
    }
    #'default': {
    #    'ENGINE': 'django.db.backends.sqlite3',
    #    'NAME': os.path.join(DATA_DIR,'db.sqlite3'),
    #}
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'HE'

TIME_ZONE = 'Asia/Jerusalem'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = (os.path.join(BASE_DIR,'locale'),)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR,'static')

TEMPLATE_DIRS = (os.path.join(BASE_DIR,'templates'),)

from django.conf import global_settings
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    "common.ctx.menu",
)

TASTYPIE_DATETIME_FORMATTING = 'iso-8601-strict'

FAKE_CUR=False

# override settings using local_settings.py
try:
    from local_settings import *
except ImportError:
    pass

if DEBUG:
    STATICFILES_DIRS = (
                        os.path.join(BASE_DIR, "tmp-trans"),
                        )



#print '#DJANGO: DEBUG = %s' % (DEBUG)

import time
LOGGING = {
    'version' : 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple' : {
            'format' : "%(asctime)s %(levelname)s %(message)s",   
        },
    }, 
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/opentrain/error.log',
            'formatter' : 'simple',
        },
    },
    'loggers': {
        'opentrain.errors': {
            'handlers': ['file'],
        },
    },
}

