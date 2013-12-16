# Initialize App Engine SDK if necessary.

from .boot import initialized, setup_env

if not initialized():
    setup_env()

from djangoappengine.utils import on_production_server, have_appserver

DEBUG = not on_production_server
TEMPLATE_DEBUG = DEBUG

ROOT_URLCONF = 'urls'

DATABASES = {
    'default': {
        'ENGINE': 'djangoappengine.db',

        # Other settings which you might want to override in your
        # settings.py.

        # Activates high-replication support for remote_api.
        'HIGH_REPLICATION': True,

        # Switch to the App Engine for Business domain.
        # 'DOMAIN': 'googleplex.com',

        # Store db.Keys as values of ForeignKey or other related
        # fields. Warning: dump your data before, and reload it after
        # changing! Defaults to False if not set.
        # 'STORE_RELATIONS_AS_DB_KEYS': True,

        'DEV_APPSERVER_OPTIONS': {
            # Optional parameters for development environment.

            # Emulate the high-replication datastore locally.
            # TODO: Likely to break loaddata (some records missing).
            'high_replication' : True,

            # Use the SQLite backend for local storage (instead of
            # default in-memory datastore). Useful for testing with
            # larger datasets or when debugging concurrency/async
            # issues (separate processes will share a common db state,
            # rather than syncing on startup).
            'use_sqlite': True,
        },
    },
}

if on_production_server:
    EMAIL_BACKEND = 'djangoappengine.mail.AsyncEmailBackend'
else:
    EMAIL_BACKEND = 'djangoappengine.mail.EmailBackend'

# Specify a queue name for the async. email backend.
EMAIL_QUEUE_NAME = 'default'

PREPARE_UPLOAD_BACKEND = 'djangoappengine.storage.prepare_upload'
SERVE_FILE_BACKEND = 'djangoappengine.storage.serve_file'
DEFAULT_FILE_STORAGE = 'djangoappengine.storage.BlobstoreStorage'
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_HANDLERS = (
    'djangoappengine.storage.BlobstoreFileUploadHandler',
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'TIMEOUT': 0,
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

if not on_production_server:
    INTERNAL_IPS = ('127.0.0.1',)

#def log_traceback(*args, **kwargs):
#    import logging
#    logging.exception("Exception in request:")

#if not on_production_server:
#    from django.core import signals
#    signals.got_request_exception.connect(log_traceback)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

if not on_production_server:
    LOGGING['handlers']['console'] = {
        'level': 'ERROR',
        'class': 'logging.StreamHandler'
    }
