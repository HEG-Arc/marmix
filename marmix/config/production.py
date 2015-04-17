# -*- coding: utf-8 -*-
'''
Production Configurations

- Use djangosecure
'''
import os
from os.path import join, dirname
from configurations import values


from .common import Common


class Production(Common):
    DEBUG = True
    # This ensures that Django will be able to detect a secure connection
    # properly on Heroku.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # INSTALLED_APPS
    INSTALLED_APPS = Common.INSTALLED_APPS
    # END INSTALLED_APPS

    # DATABASE
    DATABASES = values.DatabaseURLValue('postgres://marmix:marmix@localhost/marmix', environ_prefix='MARMIX')
    # END DATABASE

    # SECRET KEY
    SECRET_KEY = values.SecretValue(environ_prefix='MARMIX')
    # END SECRET KEY

    # django-secure
    INSTALLED_APPS += ("djangosecure", )

    # set this to 60 seconds and then to 518400 when you can prove it works
    SECURE_HSTS_SECONDS = 60
    SECURE_HSTS_INCLUDE_SUBDOMAINS = values.BooleanValue(True)
    SECURE_FRAME_DENY = values.BooleanValue(True)
    SECURE_CONTENT_TYPE_NOSNIFF = values.BooleanValue(True)
    SECURE_BROWSER_XSS_FILTER = values.BooleanValue(True)
    SESSION_COOKIE_SECURE = values.BooleanValue(False)
    SESSION_COOKIE_HTTPONLY = values.BooleanValue(True)
    #SECURE_SSL_REDIRECT = values.BooleanValue(True)
    # end django-secure

    # SITE CONFIGURATION
    # Hosts/domain names that are valid for this site
    # See https://docs.djangoproject.com/en/1.6/ref/settings/#allowed-hosts
    ALLOWED_HOSTS = ["*"]
    # END SITE CONFIGURATION

    # EMAIL
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    DEFAULT_FROM_EMAIL = values.Value('MarMix <m3@marmix.ch>')
    EMAIL_HOST = values.Value('mx.ga-fl.net')
    EMAIL_SUBJECT_PREFIX = values.Value('[MarMix] ', environ_prefix='MARMIX')
    EMAIL_USE_TLS = True
    # END EMAIL

    # TEMPLATE CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
    TEMPLATE_LOADERS = (
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        )),
    )
    # END TEMPLATE CONFIGURATION

    # CACHING
    # Only do this here because thanks to django-pylibmc-sasl and pylibmc
    # memcacheify is painful to install on windows.
    CACHES = values.CacheURLValue(default="memcached://127.0.0.1:11211", environ_prefix='MARMIX')
    # END CACHING

    ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'
    # Your production stuff: Below this line define 3rd party libary settings
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            },
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue'
            },
            },
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
            },
        'handlers': {
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class': 'django.utils.log.AdminEmailHandler'
            },
            'file_debug': {
                'level': 'INFO',
                'filters': ['require_debug_false'],
                'class': 'logging.FileHandler',
                'filename': '/var/log/marmix/django-debug.log',
                'formatter': 'verbose',
                },
            'console': {
                'level': 'DEBUG',
                'filters': ['require_debug_true'],
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                },
            },
        'loggers': {
            '': {
                'handlers': ['file_debug', 'mail_admins', 'console'],
                'level': 'DEBUG',
                'propagate': True,
                },
            }
    }
