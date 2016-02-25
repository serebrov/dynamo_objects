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
        self.expected = [{
            "city": "C2", "company_id": "YRC",
            "country": "", "store_id": "STORE3", "tags": []
        }, {
            "city": "C1", "company_id": "MYC",
            "country": "", "store_id": "STORE2", "tags": []
        }, {
            "city": "C1", "company_id": "MYC",
            "country": "", "store_id": "STORE1", "tags": []
        }]

    def test_scan_all(self):
        data = [d.get_dict() for d in self.table.scan()]
        self.assertEquals(self.expected, data)

    def test_scan_by(self):
        data = [d.get_dict() for d in self.table.scan(city__eq='C1')]
        self.assertEquals(self.expected[1:], data)

    def test_query_by_index(self):
        data = [d.get_dict() for d in self.table.query(
            company_id__eq='YRC', index='StoreCompanyIndex')]
        self.assertEquals(self.expected[:1], data)


if __name__ == "__main__":
    unittest.main()
