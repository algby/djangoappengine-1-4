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
        if not isinstance(self.pk, AncestorKey):
            return None
        ak = self.pk

        if ak._parent_cache is None:
            ak._parent_cache = ak._parent_model.objects.get(pk=ak._parent_key.id_or_name())
        return ak._parent_cache


class AncestorKey(object):
    def __init__(self, ancestor=None, key_id=None, ancestor_pk=None, ancestor_model=None):
        if ancestor is not None:
            assert ancestor.pk is not None, "You must provide a parent with a key"
            self._parent_model = type(ancestor)
            ancestor_pk = ancestor.pk
        else:
            assert ancestor_pk is not None and ancestor_model is not None, "You must provide an ancestor_model and ancestor_pk or an ancestor instance"
            self._parent_model = ancestor_model

        self._parent_key = Key.from_path(self._parent_model._meta.db_table, ancestor_pk)
        self._parent_cache = ancestor

        self.key_id = key_id or db.allocate_ids(
            self._parent_key,
            1
        )[0]

    def __eq__(self, other):
        return self._parent_key == other._parent_key and self.key_id == other.key_id


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
            return Key.from_path(
                self.model._meta.db_table,
                value.key_id,
                parent=value._parent_key
            )

        return super(GAEKeyField, self).get_db_prep_value(value, connection)
