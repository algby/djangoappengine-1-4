from django.db.models import AutoField

from google.appengine.api.datastore import Key
from google.appengine.ext import db
from django.db.models.sql.where import Constraint

class AncestorNode(Constraint):
    def __init__(self, instance):
        self.instance = instance

class PossibleDescendent(object):
    def __init__(self, *args, **kwargs):
        self._parent_key = None
        super(PossibleDescendent, self).__init__(*args, **kwargs)

    @classmethod
    def descendents_of(cls, instance):
        qs = cls.objects.all()

        #Add our own custom constraint type to mark this as an ancestor query
        #this is used in GAEQuery._decode_child and then switched for a custom filter
        #which is passed to GAEQuery.add_filter where we set the ancestor_key
        qs.query.where.add(
            (Constraint(None, '__ancestor', instance._meta.pk), 'exact', instance),
            'AND'
        )
        return qs

    def parent(self):
        return self.pk.ancestor if isinstance(self.pk, AncestorKey) else None

class AncestorKey(object):
    def __init__(self, ancestor, key_id=None):
        self.ancestor = ancestor

        parent_key = Key.from_path(ancestor._meta.db_table, ancestor.pk)
        self.key_id = key_id or db.allocate_ids(
            parent_key,
            1
        )[0]

    def __eq__(self, other):
        return self.ancestor == other.ancestor and self.key_id == other.key_id


class GAEKeyField(AutoField):
    #Make sure to_python is called on assignments
    def __init__(self, ancestor_model, *args, **kwargs):
        self.ancestor_model = ancestor_model
        self._parent_key = None
        self._id = None

        kwargs["primary_key"] = True
        super(GAEKeyField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, Key):
            return AncestorKey(
                ancestor=self.ancestor_model.objects.get(pk=value.parent().id_or_name()),
                key_id=value.id_or_name()
            )
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, AncestorKey):
            parent_key = Key.from_path(self.ancestor_model._meta.db_table, value.ancestor.pk)
            return Key.from_path(
                self.model._meta.db_table,
                value.key_id,
                parent=parent_key
            )

        return super(GAEKeyField, self).get_db_prep_value(value, connection)
