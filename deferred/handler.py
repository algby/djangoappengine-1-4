# Initialize Django.
from djangoappengine import main

from django.utils.importlib import import_module
from django.conf import settings


# Load all models.py to ensure signal handling installation or index
# loading of some apps
for app in settings.INSTALLED_APPS:
    try:
        import_module('%s.models' % (app))
    except ImportError:
        pass

# The maximum retry count on the original task queue. After that the task is reenqued on the broken-tasks queue
MAX_RETRY_COUNT = getattr(settings, 'TASK_RETRY_ON_SOURCE_QUEUE', None)
BROKEN_TASK_QUEUE = getattr(settings, 'BROKEN_TASK_QUEUE', 'broken-tasks')

import logging
from google.appengine.api import taskqueue
from google.appengine.ext.webapp import WSGIApplication
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.deferred import deferred


class LimitedTaskHandler(deferred.TaskHandler):
    def post(self):
        try:
            self.run_from_request()
        except deferred.SingularTaskFailure:
            logging.debug("Failure executing task, task retry forced")
            self.response.set_status(408)

        except deferred.PermanentTaskFailure:
            logging.exception("Permanent failure attempting to execute task")

        except Exception, exception:
            logging.exception(exception)
            retries = int(self.request.headers['X-AppEngine-TaskExecutioncount'])
            already_broken = self.request.headers['X-AppEngine-Queuename'] == BROKEN_TASK_QUEUE

            if already_broken or MAX_RETRY_COUNT is None or retries < MAX_RETRY_COUNT:
                # Failing normally
                self.error(500)
            else:
                logging.info("Retrying this task on the broken-tasks queue from now on")
                # Reinserting task onto the brokentask queue
                task = taskqueue.Task(
                    payload=self.request.body,
                    countdown=2.0,
                    url=deferred._DEFAULT_URL,
                    headers=deferred._TASKQUEUE_HEADERS
                )
                task.add(BROKEN_TASK_QUEUE)


application = WSGIApplication([(".*", LimitedTaskHandler)])


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()
