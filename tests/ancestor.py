

from django.test import TestCase
from django.db import models

from djangoappengine.fields import GAEKeyField, AncestorKey, PossibleDescendent

class AncestorModel(models.Model):
    field1 = models.CharField(default="bananas")

class ChildModel(PossibleDescendent, models.Model):
    id = GAEKeyField(ancestor_model=AncestorModel)
    field1 = models.CharField(default="apples")

class AncestorQueryTest(TestCase):
    def test_gae_key_field(self):
        parent = AncestorModel.objects.create()
        ChildModel.objects.create(id=1)

        child = ChildModel.objects.create(id=AncestorKey(parent))

        self.assertTrue(child.pk) #Should be populated
        self.assertTrue(isinstance(child.pk, (int, long)))

        self.assertTrue(child.parent())
        self.assertEqual(parent, child.parent())

        child_count = ChildModel.descendents_of(parent).filter(field1="apples").count()
        self.assertEqual(1, child_count)

        #Don't set a parent
        ChildModel.objects.create()

        #Should still be the same!
        child_count = ChildModel.descendents_of(parent).filter(field1="apples").count()
        self.assertEqual(1, child_count)


