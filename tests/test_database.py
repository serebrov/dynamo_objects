import unittest
from dynamo_objects import database
from schema import Store, StoreTable
from base import BaseDynamoTest

import os

class DbTest(BaseDynamoTest):

    def test_get_empty(self):
        with self.assertRaises(database.ItemNotFound):
            StoreTable().get('')

    def test_create_empty(self):
        store = Store()
        with self.assertRaises(database.InvalidKeysException) as context_manager:
            StoreTable().save(store)
        e = context_manager.exception
        self.assertEquals(
            "Hash / range keys for <class 'tests.schema.StoreTable'> are invalid or empty: {'store_id': None, None: None}", str(e))

    def test_wrong_field_name(self):
        store = Store(store_id=1)
        with self.assertRaises(database.DynamoSchemaException):
            store.ctiy = 'test'

    # def test_visit_get_no_range(self):
    #     message = ''
    #     keys_data = {}
    #     try:
    #         # try to get without the range key
    #         database.SessionsTable().get('AMAC|CMAC', None)
    #     except database.InvalidKeysException as e:
    #         message = e.message
    #         keys_data = e.keys_data
    #     self.assertEquals(
    #         "Hash / range keys for <class 'database.raw_wifi.SessionsTable'> are invalid or empty: {'macs': 'AMAC|CMAC', 'fseen': None}", message)
    #     self.assertEquals({'macs': 'AMAC|CMAC', 'fseen': None}, keys_data)

if __name__ == "__main__":
    unittest.main()

