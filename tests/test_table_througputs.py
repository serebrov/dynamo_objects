import unittest
from dynamo_objects import database
from .base import BaseDynamoTest
from .schema import StoreTable


class ThroughputUpdateTest(BaseDynamoTest):

    def test_update(self):
        table = StoreTable().table
        db = database.DynamoDatabase()
        old_throughputs = {
            'store': db.get_table_throughputs(table)}
        new_throughputs = {
            'store': {
                'table': {
                    'read': 100,
                    'write': 100,
                },
                'StoreCompanyIndex': {
                    'read': 20,
                    'write': 10
                }
            }
        }

        with database.TableThroughput(new_throughputs):
            # verify throughputs are updated
            self.assertEquals(new_throughputs['store'],
                              db.get_table_throughputs(table))

        # verify throughputs are changed back
        self.assertEquals(old_throughputs['store'],
                          db.get_table_throughputs(table))


if __name__ == "__main__":
    unittest.main()
