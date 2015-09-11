import time
import copy
import boto

from boto.dynamodb2.table import Table
from boto.dynamodb2.items import Item
from boto.dynamodb2.exceptions import ItemNotFound


def item_to_dict(item, deep=True, set_to_list=False):
    i = dict(item)
    for n, v in item.items():
        if type(v) == set:
            if set_to_list:
                i[n] = list(v)
            else:
                i[n] = v
        elif type(v) == dict:
            if deep:
                i[n] = item_to_dict(v, deep, set_to_list)
            else:
                del i[n]
    return i


class DynamoException(Exception):
    pass


class InvalidKeysException(DynamoException):

    def __init__(self, record, hashkey, rangekey):
        self.keys_data = {record.hashkey: hashkey, record.rangekey: rangekey}
        self.empty_keys = hashkey is None and rangekey is None
        message = (
            'Hash / range keys for %s are invalid or empty: %s' % (
                type(record),
                str(self.keys_data)))
        super(InvalidKeysException, self).__init__(message)

    def is_empty_keys(self):
        return self.empty_keys


class DynamoDatabase(object):
    _db_connection = None
    local_dynamodb = False
    table_prefix = ''
    tables = None

    def __init__(self):
        pass

    def get_connection(self):
        if DynamoDatabase._db_connection is None:
            raise DynamoException('No connection, use connect() method to connect to the database')
        return DynamoDatabase._db_connection

    def connect(self, **kwargs):
        if 'table_prefix' in kwargs:
            DynamoDatabase.table_prefix = kwargs['table_prefix']
            del kwargs['table_prefix']
        if DynamoDatabase._db_connection is not None:
            raise DynamoException('Already connected, use disconnect() before making a new connection')
        if 'region_name' in kwargs and kwargs['region_name'] == 'localhost': # local dynamodb
            DynamoDatabase._db_connection = boto.dynamodb2.layer1.DynamoDBConnection(
                host='localhost',
                port=kwargs.get('DYNAMODB_PORT', 8000),
                aws_access_key_id='local',
                aws_secret_access_key='success',
                is_secure=False)
            DynamoDatabase.local_dynamodb = True
        else: # Real dynamo db
            DynamoDatabase._db_connection = boto.dynamodb2.connect_to_region(**kwargs)
        self.get_tables()
        return DynamoDatabase._db_connection

    def disconnect(self):
        if DynamoDatabase._db_connection is not None:
            del DynamoDatabase._db_connection
            DynamoDatabase._db_connection = None

    def connected(self):
        return DynamoDatabase._db_connection is not None

    def is_local_db(self):
        if self.get_connection():
            return DynamoDatabase.local_dynamodb

    def get_tables(self):
        DynamoDatabase.tables = self.get_connection().list_tables()
        if not DynamoDatabase.tables:
            raise DynamoException('Unable to get database tables, connection: %s' % str(DynamoDatabase.db_connection))
        return DynamoDatabase.tables['TableNames']

    def get_table_name(self, table_name):
        return DynamoDatabase.table_prefix + table_name

    def exists(self, table_name):
        if self.get_connection():
            return self.get_table_name(table_name) in DynamoDatabase.tables['TableNames']
        return False

    def check_exists(self, table):
        try:
            table.describe()
        except boto.exception.JSONResponseError as e:
            if e.body['__type'] == 'com.amazonaws.dynamodb.v20120810#ResourceNotFoundException':
                return False
            raise
        return True

    def create_table(self, table_name, schema, throughput, indexes=None, global_indexes=None):
        Table.create(self.get_table_name(table_name), schema=schema, throughput=throughput, connection=self.get_connection(), indexes=indexes, global_indexes=global_indexes)
        self.wait_table_active(table_name)
        self.get_tables()

    def get_table(self, table_name):
        return Table(self.get_table_name(table_name), connection=self.get_connection())

    def get_table_raw(self, table_name):
        return Table(table_name, connection=self.get_connection())

    def get_table_key(self, table_name):
        table = self.get_table(table_name)
        table.describe()
        hashkey = table.schema[0].name
        rangekey = None
        if len(table.schema) > 1:
            rangekey = table.schema[1].name
        return (hashkey, rangekey)

    def copy_item(self, item_from, table_name_to, update=False):
        table_to = self.get_table(table_name_to)
        (hashkey, rangekey) = self.get_table_key(table_name_to)
        key_data = {hashkey: item_from[hashkey]}
        if rangekey:
            key_data[rangekey] = item_from[rangekey]

        try:
            item_to = table_to.get_item(**key_data)
            if not update:
                raise DynamoException('Item already exists: %s in %s' % (key_data, table_name_to))
        except ItemNotFound as inf:
            item_to = Item(table_to, key_data)
        for k, v in item_from.items():
            item_to[k] = v
        return item_to

    def copy_table_data(
        self, table_name_from, table_name_to,
        update=False, progress=None,
        transform=None
    ):
        table_from = self.get_table(table_name_from)
        data = table_from.scan()
        num_moved = 0
        for record in data:
            try:
                elem = self.copy_item(record, table_name_to, update)
                if transform:
                    transform(elem)
                elem.save()
                if progress:
                    progress.update(1)
                num_moved += 1
            except:
                progress.update(0)
                # skip errors when item already exists
                # just move the new data
                #pass
                raise
        return num_moved

    def wait_table_active(self, table_name):
        table = self.get_table(table_name)
        while True:
            status = table.describe()['Table']['TableStatus']
            if status == 'ACTIVE':
                break
            time.sleep(1)

    def delete_table(self, table_name):
        try:
            self.db.get_table(table_name).delete()
        except:
            return False
        while True:
            if self.exists(table_name):
                time.sleep(1)
                self.get_tables()
            else:
                return True

    def get_table_throughputs(self, table):
        info = table.describe()['Table']
        result = {
            'table': {
                'write': info['ProvisionedThroughput']['WriteCapacityUnits'],
                'read': info['ProvisionedThroughput']['ReadCapacityUnits']
            }
        }
        if 'GlobalSecondaryIndexes' in info:
            for index_info in info['GlobalSecondaryIndexes']:
                result[index_info['IndexName']] = {
                    'read': index_info['ProvisionedThroughput']['ReadCapacityUnits'],
                    'write': index_info['ProvisionedThroughput']['WriteCapacityUnits']
                }
        return result


class TablesThroughput(object):
    """
    Can be used to update / restore tables throughput for batch operations.
    """
    def __init__(self, throughputs, old_throughputs=None, restore=True, wait_enter=True, wait_exit=False):
        """
        throughputs - {
            'table_name1': {'table': {'write':100,'read':100'}},
            'table_name2': {
                'table': {'write':10,'read':15},
                # for global secondary indexes
                'MyIndex1': {'read':1,'write':10'}
        }
        """
        self.db = DynamoDatabase()
        self.restore = restore
        self.wait_enter = wait_enter
        self.wait_exit = wait_exit
        self._new_throughputs = throughputs
        if old_throughputs is not None:
            self. _old_throughputs = old_throughputs
        else:
            self._old_throughputs = {}
        self._tables = {}
        for table_name in throughputs:
            table = self.db.get_table(table_name)
            self._tables[table_name] = table
            if old_throughputs is None:
                self._old_throughputs[table_name] = self.db.get_table_throughputs(table)

    def __enter__(self):
        self.update_throughputs(self._new_throughputs, self.wait_enter)
        return self

    def __exit__(self, type, value, traceback):
        if self.restore:
            self.update_throughputs(self._old_throughputs, self.wait_exit)

    def update_throughputs(self, throughputs, wait):
        for table_name in throughputs:
            table = self._tables[table_name]
            data = throughputs[table_name]
            throughput = None
            gsi = None
            for index_name in data:
                if index_name == 'table':
                    throughput = data['table']
                else:
                    if gsi is None:
                        gsi = {}
                    idata = data[index_name]
                    gsi[index_name] = {
                        'write': idata['write'],
                        'read': idata['read']
                    }
            try:
                table.update(throughput, gsi)
            except boto.exception.JSONResponseError as e:
                if (
                    e.body["__type"] ==
                    "com.amazonaws.dynamodb.v20120810#LimitExceededException"
                    and self.db.is_local_db()
                ):
                    # for some reason local dynamo db does not allow to
                    # increase throughput more than twice
                    print e.body['Message']
                else:
                    raise
        if wait:
            for table_name in throughputs:
                self.db.wait_table_active(table_name)

    def _get_gsi_info(table_info, index_name):
        for idx in table_info['GlobalSecondaryIndexes']:
            if idx['IndexName'] == index_name:
                return idx
        raise DynamoException('Index %s not found' % index_name)


class DynamoRecord(object):

    def __init__(self, **data):
        self._item = None
        self.check_attrs(data)
        self.update_data(**data)
        self._check_data()

    def update_data(self, **data):
        self.__dict__.update(data)

    def check_attrs(self, data):
        for key in data:
            if not hasattr(self, key):
                raise DynamoException(
                    "DynamoRecord %s doesn't have '%s' attribute" %
                    (self.__class__, key)
                )

    def get_dict(self, exclude=None):
        exclude = exclude or []
        self._check_data()
        data = copy.copy(self.__dict__)
        for key in self.__dict__:
            if key.startswith('_') or key in exclude:
                del data[key]
        return data

    def _check_data(self):
        pass


class DynamoTable(object):

    # Create a new record and save it
    #
    #   record = MyRecord(hash='value1', range='value2', field1='x')
    #   record.field2 = 100
    #   MyRecordTable().save(record)
    #
    #
    # Find or create record, change data and save:
    #
    #   table = MyRecordTable()
    #   # get a record or create new one
    #   record = table.get('value1', 'value2', create=True)
    #   record.field1 = 100
    #   table.save(record)
    #
    # The 'create=True' option is also useful if you whether read data from
    # db or need to get Null-object with sane empty defaults, like
    #
    #  class User(DynamoRecord):
    #
    #    def __init__(self, *data):
    #       self.name = 'guest'
    #       self.password = ''
    #       super(User, self).__init__(**data)
    #
    #  user = table.get(user_id, create=True)
    #  # print user name or 'guest' (default)
    #  print user.name
    #
    # Delete record:
    #
    #   # will return deleted record
    #   record = table.delete('hash', 'range')
    #
    # Query:
    #
    #   # parameters are the same as for boto's query_2
    #   # returns array of records
    #   # don't use when you expect a lot of data, because it will
    #   # fetch all the data from the database and convert to DynamoRecord
    #   # before returning
    #   records = table.query(hash__eq='value', range__gte=50')
    #

    def __init__(self, table_name, schema, throughput, record_class, global_indexes=None):
        self.db = DynamoDatabase()
        self.table_name = table_name
        self.schema = schema
        self.global_indexes = global_indexes
        self.throughput = throughput
        self.record_class = record_class
        if not self.db.exists(self.table_name):
            self._create_table()
        self.table = self.db.get_table(self.table_name)
        self.hashkey = self.schema[0].name
        self.rangekey = None
        if len(self.schema) > 1:
            self.rangekey = self.schema[1].name

    def get(self, hashkey, rangekey=None, create=False):
        try:
            keys_data = self._get_keys_dict(hashkey, rangekey)
        except InvalidKeysException as e:
            # if we do something like MyTable().get('') - raise
            # ItemNotFound (nothing found)
            if e.is_empty_keys():
                raise ItemNotFound()
            else:
                # if keys were invalid (like range is needed, but not given)
                # then re-raise an exception
                raise
        try:
            item = self._get_boto_item(keys_data)
        except ItemNotFound:
            # create the new item if requested
            # or raise the ItemNotFound otherwise
            if create:
                cls = self.record_class
                return cls(**keys_data)
            raise
        return self._create_record_for_item(item)

    def find(self, hashkey, rangekey=None, default=None):
        try:
            return self.get(hashkey, rangekey)
        except ItemNotFound:
            return default

    def delete(self, hashkey, rangekey=None):
        item = self.table.get_item(**self._get_keys_dict(hashkey, rangekey))
        item.delete()
        return self._create_record_for_item(item)

    def save(self, record):
        # verify that keys are valid
        self._get_record_keys(record)
        item = self._get_item_for_record(record)
        if record._item:
            # update existing record
            item.partial_save()
        else:
            # new item was created, full save
            item.save()

    def query(self, **kwargs):
        items = self.table.query_2(**kwargs)
        return map(lambda item: self._create_record_for_item(item), items)

    def scan(self, **kwargs):
        items = self.table.scan(**kwargs)
        return map(lambda item: self._create_record_for_item(item), items)

    def _get_boto_item(self, keys_data):
        return self.table.get_item(**keys_data)

    def _create_table(self):
        self.db.create_table(
            table_name=self.table_name,
            schema=self.schema,
            global_indexes=self.global_indexes,
            throughput=self.throughput)

    def _check_keys(self, hashkey, rangekey=None):
        data = {}
        if self.rangekey:
            if hashkey is None or rangekey is None:
                raise InvalidKeysException(self, hashkey, rangekey)
            data = {self.hashkey: hashkey, self.rangekey: rangekey}
        else:
            if hashkey is None or rangekey is not None:
                raise InvalidKeysException(self, hashkey, rangekey)
            data = {self.hashkey: hashkey}
        # check if values are saveable to dynamodb
        data = self._get_safe_data(data)
        if self.hashkey not in data:
            raise InvalidKeysException(self, None, None)
        if self.rangekey and self.rangekey not in data:
            raise InvalidKeysException(self, hashkey, None)
        return (hashkey, rangekey)

    def _get_record_keys(self, record):
        hashkey = getattr(record, self.hashkey)
        rangekey = None
        if self.rangekey:
            rangekey = getattr(record, self.rangekey)
        return self._check_keys(hashkey, rangekey)

    def _get_keys_dict(self, hashkey, rangekey=None):
        keys = self._check_keys(hashkey, rangekey)
        key_data = {self.hashkey: keys[0]}
        if self.rangekey:
            key_data[self.rangekey] = keys[1]
        return key_data

    def _get_safe_data(self, dictionary, checker=None):
        checker = checker or Item(self.table)
        data = {}
        for key in dictionary:
            if isinstance(dictionary[key], dict):
                data[key] = self._get_safe_data(dictionary[key], checker)
            elif checker._is_storable(dictionary[key]):
                data[key] = dictionary[key]
        return data

    def _get_item_for_record(self, record):
        if record._item:
            item = record._item
            data = record.get_dict()
            for key in data:
                if item._is_storable(data[key]) or key in item:
                    # only copy storable fields or those we want to reset
                    # for example, if item['name']='Bob' we can set it to ''
                    # but if item didn't have 'name' field then we should
                    # not set it (dynamodb does not allow empty fields)
                    item[key] = data[key]
            return item
        else:
            data = self._get_safe_data(record.get_dict())
            item = Item(self.table, data=data)
            return item

    def _create_record(self, hashkey, rangekey=None):
        cls = self.record_class
        record = cls(**self._get_keys_dict(hashkey, rangekey))
        return record

    def _create_record_for_item(self, item):
        """Create a db record from Item.

        :item: boto Item object
        :returns: new db record object

        """
        # if item is None:
        #     return None
        cls = self.record_class
        obj = cls(**item_to_dict(item))
        obj._item = item
        return obj
