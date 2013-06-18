import os

from google.appengine.api import apiproxy_stub_map
from google.appengine.api.app_identity import get_application_id
from google.appengine.api.datastore import Entity, Put

have_appserver = bool(apiproxy_stub_map.apiproxy.GetStub('datastore_v3'))

if not have_appserver:
    from .boot import PROJECT_DIR
    from google.appengine.tools import dev_appserver
    appconfig = dev_appserver.LoadAppConfig(PROJECT_DIR, {},
                                                    default_partition='dev')[0]
def appid():
    if have_appserver:
        return get_application_id()
    else:
        try:
            return appconfig.application.split('~', 1)[-1]
        except ImportError, e:
            raise Exception("Could not get appid. Is your app.yaml file missing? "
                            "Error was: %s" % e)

on_production_server = 'SERVER_SOFTWARE' in os.environ and not os.environ['SERVER_SOFTWARE'].startswith("Development")


def bulk_create(instances, connection=None):
    """
        Uses AppEngine's bulk Put() call on a number of instances
        this will NOT call save() but it will return the instances
        with their primary_key populated (unlike Django's bulk_create)
    """
    if connection is None:
        from django.db import connection

    from .fields import AncestorKey

    def prepare_entity(instance):
        if isinstance(instance.pk, AncestorKey):
            parent = instance.pk._parent_key
        else:
            parent = None

        result = Entity(instance._meta.db_table, parent=parent)

        for field in instance._meta.fields:
            if field.name == "id":
                continue

            value = field.pre_save(instance, True)
            setattr(instance, field.name, value)
            value = field.get_db_prep_save(getattr(instance, field.attname), connection)
            if isinstance(value, (list, set)):
                value = list(value)
                if not value:
                    value = None

            result[field.column] = value
        return result

    entities = [ prepare_entity(x) for x in instances ]

    keys = Put(entities)

    assert(len(keys) == len(entities))

    for i, key in enumerate(keys):
        assert(key)

        if key.parent():
            instances[i]._parent_key = key.parent()
            instances[i].pk.key_id = key.id_or_name()
        else:
            instances[i].id = key.id_or_name()

    return instances

