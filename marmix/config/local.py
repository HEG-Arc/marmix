# -*- coding: utf-8 -*-
'''
Local Configurations

- Runs in Debug mode
- Uses console backend for emails
- Use Django Debug Toolbar
'''
from configurations import values
from .common import Common


class Local(Common):

    # DEBUG
    DEBUG = values.BooleanValue(True)
    TEMPLATE_DEBUG = DEBUG
    # END DEBUG

    # INSTALLED_APPS
    INSTALLED_APPS = Common.INSTALLED_APPS
    # END INSTALLED_APPS

    # Mail settings
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 1025
    EMAIL_BACKEND = values.Value('django.core.mail.backends.console.EmailBackend')
    # End mail settings

    # django-debug-toolbar
    MIDDLEWARE_CLASSES = Common.MIDDLEWARE_CLASSES + ('debug_toolbar.middleware.DebugToolbarMiddleware',)
    INSTALLED_APPS += ('debug_toolbar',)

    INTERNAL_IPS = ('127.0.0.1', '10.0.2.2',)

    # MSSQL
    MSSQL_HOST = values.Value('data.marmix.ch', environ_prefix='MARMIX')
    MSSQL_DATABASE = values.Value('test', environ_prefix='MARMIX')
    MSSQL_USER = values.Value('test', environ_prefix='MARMIX')
    MSSQL_PASSWORD = values.SecretValue(environ_prefix='MARMIX')

    DEBUG_TOOLBAR_CONFIG = {
        'DISABLE_PANELS': [
            'debug_toolbar.panels.redirects.RedirectsPanel',
        ],
        'SHOW_TEMPLATE_CONTEXT': True,
        'JQUERY_URL': '/static/jquery/js/jquery-2.1.0.min.js',
    }
    # end django-debug-toolbar

    # django-nose
    INSTALLED_APPS += ('django_nose',)

    # Use nose to run all tests
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

    # Tell nose to measure coverage on the 'foo' and 'bar' apps
    NOSE_ARGS = [
        '--with-coverage',
        '--cover-package=stocks, users',
    ]

    INSTALLED_APPS += ('django_extensions',)

    ALLOWED_HOSTS = ["*"]
