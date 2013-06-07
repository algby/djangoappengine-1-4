Djangoappengine, a Django database backend for App Engine
=========================================================

Documentation at http://readthedocs.org/docs/django-nonrel/en/latest/

Djangoappengine allows you to use App Engine's datastore with
Django. It provides the necessary plumbing to query the datastore, and
custom management commands for deploying and running the SDK.

Contributing
------------
You are highly encouraged to participate in the development, simply use
GitHub's fork/pull request system.

If you don't like GitHub (for some reason) you're welcome
to send regular patches to the mailing list.

:Mailing list: http://groups.google.com/group/django-non-relational
:Bug tracker: https://github.com/django-nonrel/djangoappengine/issues
:License: 3-clause BSD, see LICENSE
:Keywords: django, app engine, orm, nosql, database, python

#Setting up your WSGI handler

Djangoappengine now uses WSGI middleware to workaround some issues in AppEngine's
environment variable handling when threadsafe is true, and also to clean up the code.

These changes break compatibilty with Python 2.5 so if you need that, either use the
official djangoappengine, or use an older revision.

Your wsgi.py should now look something like this:

    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myapp.settings")

    from djangoappengine.main import DjangoAppEngineMiddleware
    from django.core.wsgi import get_wsgi_application

    application = DjangoAppEngineMiddleware(get_wsgi_application())

And the magic should just work!

# Ancestor Queries

Ancestor queries are very datastore specific, but this fork of Djangoappengine includes
basic support for them. To use ancestor queries you must do the following:

1. Replace your "id" field of your child model with a djangoappengine.fields.GAEKeyField. e.g.

    id = GAEKeyField(ancestor_model=AncestorModel)

2. Make your child model use the PossibleDescendent Mixin, e.g.

    class ChildModel(PossibleDescendent, models.Model):
        id = GAEKeyField(ancestor_model=AncestorModel)

Now, you can do the following:

    parent = AncestorModel.objects.create()
    child = ChildModel.objects.create(id=AncestorKey(parent))

    child.parent() == parent

    children = ChildModel.descendents_of(parent).all()

You can continue to use child and ancestor models as normal if you want:

    child = ChildModel.objects.create()
    child.parent() -> None
