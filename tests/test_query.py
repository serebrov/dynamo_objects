import unittest
from dynamo_objects import database
from .base import BaseDynamoTest
from .schema import Store, StoreTable


class QueryTest(BaseDynamoTest):

    def setUp(self):
        super(QueryTest, self).setUp()
        self.table = StoreTable()
        store = Store(store_id='STORE1', company_id='MYC', city='C1')
        self.table.save(store)
        store = Store(store_id='STORE2', company_id='MYC', city='C1')
        self.table.save(store)
        store = Store(store_id='STORE3', company_id='YRC', city='C2')
        self.table.save(store)
        self.expected = {
            'STORE3': {
                "city": "C2", "company_id": "YRC",
                "country": "", "store_id": "STORE3", "tags": []
            },
            'STORE2': {
                "city": "C1", "company_id": "MYC",
                "country": "", "store_id": "STORE2", "tags": []
            },
            'STORE1': {
                "city": "C1", "company_id": "MYC",
                "country": "", "store_id": "STORE1", "tags": []
            }
        }

    def test_scan_all(self):
        data = [d.get_dict() for d in self.table.scan()]
        for store in data:
            self.assertEquals(self.expected[store['store_id']], store)

    def test_scan_by(self):
        data = [d.get_dict() for d in self.table.scan(city__eq='C1')]
        for store in data:
            self.assertEquals(self.expected[store['store_id']], store)

    def test_query_by_index(self):
        data = [d.get_dict() for d in self.table.query(
            company_id__eq='YRC', index='StoreCompanyIndex')]
        for store in data:
            self.assertEquals(self.expected[store['store_id']], store)

    def test_query_count(self):
        self.assertEquals(1, self.table.query_count(
            company_id__eq='YRC', index='StoreCompanyIndex'))


if __name__ == "__main__":
    unittest.main()
