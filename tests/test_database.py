import unittest
from dynamo_objects import database
from .base import BaseDynamoTest
from .schema import Store, StoreTable


class DbTest(BaseDynamoTest):

    def test_get_empty(self):
        with self.assertRaises(database.ItemNotFound):
            StoreTable().get('')

    def test_create_empty(self):
        store = Store()
        with self.assertRaises(database.InvalidKeysException) as cm:
            StoreTable().save(store)
        e = cm.exception
        self.assertEquals(
            "Hash / range keys for <class 'tests.schema.StoreTable'> are "
            "invalid or empty: {'store_id': None, None: None}", str(e))

    def test_wrong_field_name(self):
        store = Store(store_id=1)
        with self.assertRaises(database.DynamoSchemaException):
            store.ctiy = 'test'


if __name__ == "__main__":
    unittest.main()
