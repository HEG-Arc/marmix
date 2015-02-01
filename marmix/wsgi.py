"""
WSGI config for MarMix.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os
from django.core.handlers.wsgi import WSGIHandler
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.production")
os.environ.setdefault("DJANGO_CONFIGURATION", "Production")

application = get_wsgi_application()

class WSGIEnvironment(WSGIHandler):

    def __call__(self, environ, start_response):

        os.environ['MARMIX_TRAVIS_TOKEN'] = environ['MARMIX_TRAVIS_TOKEN']
        os.environ['MARMIX_TRAVIS_REPO_SLUG'] = environ['MARMIX_TRAVIS_REPO_SLUG']
        os.environ['MARMIX_SECRET_KEY'] = environ['MARMIX_SECRET_KEY']
        os.environ['MARMIX_DATABASE_URL'] = environ['MARMIX_DATABASE_URL']
        os.environ['MARMIX_CACHE_URL'] = environ['MARMIX_CACHE_URL']
        return super(WSGIEnvironment, self).__call__(environ, start_response)

#application = WSGIEnvironment()
