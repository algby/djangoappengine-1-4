

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
        self.assertTrue(isinstance(child.pk, AncestorKey))

        self.assertTrue(child.parent())
        self.assertEqual(parent, child.parent())

        child_count = ChildModel.descendents_of(parent).filter(field1="apples").count()
        self.assertEqual(1, child_count)

        #Don't set a parent
        non_child = ChildModel.objects.create()

        #Should still be the same!
        child_count = ChildModel.descendents_of(parent).filter(field1="apples").count()
        self.assertEqual(1, child_count)

        #Create another child
        child2 = ChildModel.objects.create(id=AncestorKey(parent))

        child_count = ChildModel.descendents_of(parent).filter(field1="apples").count()
        self.assertEqual(2, child_count)

        #Check that we can still get the children by their ID like normal
        pk = child.pk
        child = ChildModel.objects.get(pk=pk)
        self.assertEqual(pk, child.pk)
        self.assertTrue(child.parent())

        pk = child2.pk
        child2 = ChildModel.objects.get(pk=pk)
        self.assertEqual(pk, child2.pk)
        self.assertTrue(child2.parent())

        pk = non_child.pk
        non_child = ChildModel.objects.get(pk=pk)
        self.assertEqual(pk, non_child.pk)
        self.assertIsNone(non_child.parent())

        #Check all children are returned without the ancestor query
        child_count = ChildModel.objects.filter(field1="apples").count()
        self.assertEqual(4, child_count)

        child_count = ChildModel.descendents_of(parent).filter(field1="apples").count()
        self.assertEqual(2, child_count)
