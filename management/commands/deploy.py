import logging
import time
import sys
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from ...boot import PROJECT_DIR
from ...utils import appconfig
from subprocess import check_output, PIPE, Popen

PRE_DEPLOY_COMMANDS = ()
if 'mediagenerator' in settings.INSTALLED_APPS:
    PRE_DEPLOY_COMMANDS += ('generatemedia',)
PRE_DEPLOY_COMMANDS = getattr(settings, 'PRE_DEPLOY_COMMANDS',
                              PRE_DEPLOY_COMMANDS)
POST_DEPLOY_COMMANDS = getattr(settings, 'POST_DEPLOY_COMMANDS', ())


def run_appcfg(argv):
    # We don't really want to use that one though, it just executes
    # this one.
    from google.appengine.tools import appcfg

    # Reset the logging level to WARN as appcfg will spew tons of logs
    # on INFO.
    logging.getLogger().setLevel(logging.WARN)

    new_args = argv[:]
    new_args[1] = 'update'
    if appconfig.runtime != 'python':
        new_args.insert(1, '-R')
    new_args.append(PROJECT_DIR)
    syncdb = True
    if '--nosyncdb' in new_args:
        syncdb = False
        new_args.remove('--nosyncdb')
    appcfg.main(new_args)

    from ...db.stubs import stub_manager

    if syncdb:
        print "Running syncdb."
        # Wait a little bit for deployment to finish.
        for countdown in range(9, 0, -1):
            sys.stdout.write('%s\r' % countdown)
            time.sleep(1)
        from django.db import connections

        for connection in connections.all():
            #If we don't support joins, assume this is the datastore
            if not connection.features.supports_joins:
                stub_manager.setup_remote_stubs(connection)
        call_command('syncdb', remote=True, interactive=True)

    if getattr(settings, 'ENABLE_PROFILER', False):
        print "--------------------------\n" \
              "WARNING: PROFILER ENABLED!\n" \
              "--------------------------"


class Command(BaseCommand):
    """
    Deploys the website to the production server.

    Any additional arguments are passed directly to appcfg.py update.
    """
    help = "Calls appcfg.py update for the current project."
    args = "[any appcfg.py options]"

    def run_from_argv(self, argv):
        from djangoappengine.boot import PROJECT_DIR
        app_yaml = open(os.path.join(PROJECT_DIR, "app.yaml")).read()

        app_version = app_yaml.split("version:")[1].lstrip().split()[0]
        app_name = app_yaml.split("application:")[1].lstrip().split()[0]

        os.environ['DEFAULT_VERSION_HOSTNAME'] = "%s.appspot.com" % app_name
        os.environ['APPLICATION_ID'] = "s~" + app_name
        os.environ['CURRENT_VERSION_ID'] = app_version

        for command in PRE_DEPLOY_COMMANDS:
            if isinstance(command, (list, tuple)):
                #If this is a path to a binary, then run that with the arguments
                if os.path.exists(command[0]):
                    p = Popen(command, stdin=sys.stdin, stdout=sys.stdout)
                    p.communicate()
                else:
                    call_command(command[0], *command[1], **command[2])
            else:
                call_command(command)
        try:
            run_appcfg(argv)
        finally:
            for command in POST_DEPLOY_COMMANDS:
                if isinstance(command, (list, tuple)):
                    #If this is a path to a binary, then run that with the arguments
                    if os.path.exists(command[0]):
                        p = Popen(command, stdin=sys.stdin, stdout=sys.stdout)
                        p.communicate()
                    else:
                        call_command(command[0], *command[1], **command[2])
                else:
                    call_command(command)
