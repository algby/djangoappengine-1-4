import logging
import os
from django.utils.importlib import import_module

def validate_models():
    """
    Since BaseRunserverCommand is only run once, we need to call
    model valdidation here to ensure it is run every time the code
    changes.
    """
    from django.core.management.validation import get_validation_errors
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

    logging.info("Validating models...")

    s = StringIO()
    num_errors = get_validation_errors(s, None)

    if num_errors:
        s.seek(0)
        error_text = s.read()
        logging.critical("One or more models did not validate:\n%s" %
                         error_text)
    else:
        logging.info("All models validated.")

from djangoappengine.utils import on_production_server
if not on_production_server:
    validate_models()

class DjangoAppEngineMiddleware:
    def __init__(self, app, setup_signals=False):
        self.settings_module = os.environ['DJANGO_SETTINGS_MODULE']

        from djangoappengine.boot import setup_env
        setup_env()

        from django.conf import settings

        if setup_signals:
            # Load all models.py to ensure signal handling installation or index
            # loading of some apps.
            for app_to_import in settings.INSTALLED_APPS:
                try:
                    import_module('%s.models' % app_to_import)
                except ImportError:
                    pass

        ## In vanilla Django, staticfiles overrides runserver to use StaticFilesHandler
        ## if necessary. As we can't do this in our runserver (because we handover to dev_appserver)
        ## this has to be done here
        if (not on_production_server and settings.DEBUG) and 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
            from django.contrib.staticfiles.handlers import StaticFilesHandler
            app = StaticFilesHandler(app)

        if getattr(settings, 'ENABLE_APPSTATS', False):
            from google.appengine.ext.appstats.recording import \
                appstats_wsgi_middleware
            app = appstats_wsgi_middleware(app)

        self.wrapped_app = app

    def __call__(self, environ, start_response):
        #Always make sure the settings module is set - AppEngine sometimes loses it!
        os.environ['DJANGO_SETTINGS_MODULE'] = self.settings_module
        return self.wrapped_app(environ, start_response)
