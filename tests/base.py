import unittest
from dynamo_objects import database

import os

DYNAMODB_MOCK = bool(os.environ['DYNAMODB_MOCK']) if 'DYNAMODB_MOCK' in os.environ else True

TABLE_PREFIX = 'zz_unit_test_'
if DYNAMODB_MOCK:
    print 'Using mockup db'
else:
    print 'Using local dynamodb'

if DYNAMODB_MOCK:
    from dynamo_objects import dynamock


class BaseDynamoTest(unittest.TestCase):

    def setUp(self):
        if not database.DynamoDatabase().connected():
            database.DynamoDatabase().connect(
                region_name='localhost',
                table_prefix=TABLE_PREFIX
            )
