from google.appengine.ext import db
from django.core.management.commands.loaddata import Command as BaseLoaddataCommand
from django.db.models.signals import post_save


class Command(BaseLoaddataCommand):
    def handle(self, *a, **kw):

        def reserve_id(sender, instance, created, raw, *args, **kwargs):
            if kwargs.get('using', None) != 'default':
                return
            db.allocate_id_range(db.Key.from_path(instance._meta.db_table, 1), instance.pk, instance.pk)

        post_save.connect(receiver=reserve_id)
        super(Command, self).handle(*a, **kw)
        post_save.disconnect(reserve_id)
