import sys
import unittest
from dynamo_objects import database

import os

DYNAMODB_MOCK = bool(os.environ['DYNAMODB_MOCK']) \
    if 'DYNAMODB_MOCK' in os.environ else True

TABLE_PREFIX = 'zz_unit_test_'
if DYNAMODB_MOCK:
    sys.stdout.writelines('Using mockup db')
else:
    sys.stdout.writelines('Using local dynamodb')

if DYNAMODB_MOCK:
    from dynamo_objects import dynamock


class BaseDynamoTest(unittest.TestCase):

    def setUp(self):
        self.db = database.DynamoDatabase()
        if not self.db.connected():
            self.db.connect(
                # debug=2,
                region_name='localhost',
                table_prefix=TABLE_PREFIX
            )
        if DYNAMODB_MOCK:
            # reset the mock db before each test
            self.db.get_connection().reset()
        else:
            # or ensure that we have the local dynamodb, not the real one
            self.assertTrue(self.db.is_local_db())
            tables = self.db.get_tables()
            if tables:
                for name in tables:
                    if name.startswith(TABLE_PREFIX):
                        table = self.db.get_table_raw(name)
                        table.delete()
                        while self.db.check_exists(table):
                            time.sleep(.5)
            self.db.get_tables()
