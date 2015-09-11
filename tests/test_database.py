import unittest
from dynamo_objects import database
from schema import Store, StoreTable
from base import BaseDynamoTest

import os

class DbTest(BaseDynamoTest):

    def test_store_get_empty(self):
        result = False
        try:
            StoreTable().get('')
        except database.ItemNotFound:
            result = True
        self.assertTrue(result)

    def test_store_create_empty(self):
        message = ''
        try:
            store = Store()
            StoreTable().save(store)
        except database.InvalidKeysException as e:
            message = e.message
        self.assertEquals(
            "Hash / range keys for <class 'schema.StoreTable'> are invalid or empty: {'store_id': None, None: None}", message)

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

