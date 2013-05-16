from djangoappengine.boot import setup_env
setup_env()

def validate_models():
    """
    Since BaseRunserverCommand is only run once, we need to call
    model valdidation here to ensure it is run every time the code
    changes.
    """
    import logging
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

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from django.conf import settings

## In vanilla Django, staticfiles overrides runserver to use StaticFilesHandler
## if necessary. As we can't do this in our runserver (because we handover to dev_appserver)
## this has to be done here
if (not on_production_server and settings.DEBUG) and 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    application = StaticFilesHandler(application)

if getattr(settings, 'ENABLE_APPSTATS', False):
    from google.appengine.ext.appstats.recording import \
        appstats_wsgi_middleware
    application = appstats_wsgi_middleware(application)
