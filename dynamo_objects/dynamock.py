from collections import defaultdict

from boto.dynamodb2.fields import HashKey, RangeKey
from boto.dynamodb2.exceptions import ItemNotFound
from boto.dynamodb.types import Dynamizer


def mock_item_to_dict(item, deep=True, set_to_list=False):
    i = dict()
    for n in item:
        v = item[n]
        if type(v) == set:
            if set_to_list:
                i[n] = list(v)
            else:
                i[n] = v
        elif type(v) == dict:
            if deep:
                i[n] = mock_item_to_dict(v, deep, set_to_list)
        else:
            i[n] = v
    return i


class Connection(dict):

    def __init__(self, **kwargs):
        pass

    def create_table(self, attribute_definitions, table_name, key_schema,
                     provisioned_throughput, local_secondary_indexes=None,
                     global_secondary_indexes=None):
        self[table_name] = {'hashkey': '', 'rangekey': ''}
        for key in key_schema:
            if isinstance(key, HashKey):
                self[table_name]['hashkey'] = key.name
            if isinstance(key, RangeKey):
                self[table_name]['rangekey'] = key.name
        self[table_name]['data'] = defaultdict(lambda: defaultdict(dict))
        self[table_name]['meta'] = {
            'throughput': provisioned_throughput,
            'local_indexes': local_secondary_indexes,
            'global_indexes': global_secondary_indexes
        }

    def list_tables(self):
        return {'TableNames': self.keys()}

    def reset(self):
        for table_name in self.keys():
            self[table_name]['data'] = defaultdict(lambda: defaultdict(dict))

    def update_item(self, table_name, key, attribute_updates=None,
                    expected=None, conditional_operator=None,
                    return_values=None, return_consumed_capacity=None,
                    return_item_collection_metrics=None,
                    update_expression=None, condition_expression=None,
                    expression_attribute_names=None,
                    expression_attribute_values=None):
        """Update item low-level method.
           Warning: support is very limited, only to counter updates
        """
        table = Table(table_name, self)
        table.update_item(
            key, attribute_updates,
            expected, conditional_operator,
            return_values, return_consumed_capacity,
            return_item_collection_metrics,
            update_expression, condition_expression,
            expression_attribute_names,
            expression_attribute_values)


class Table:

    def __init__(self, table_name, connection):
        self.table_name = table_name
        self.connection = connection
        self.hashkey = connection[table_name]['hashkey']
        self.rangekey = connection[table_name]['rangekey']
        self.meta = connection[table_name]['meta']
        self.data = connection[table_name]['data']

    @classmethod
    def create(
        cls, table_name, schema, throughput, connection,
        indexes=None, global_indexes=None
    ):
        connection.create_table(
            table_name=table_name,
            attribute_definitions=schema,
            key_schema=schema,
            provisioned_throughput=throughput,
            local_secondary_indexes=indexes,
            global_secondary_indexes=global_indexes
        )
        return Table(table_name, connection)

    def get_item(self, **kwargs):
        if kwargs[self.hashkey] not in self.data:
            raise ItemNotFound()
        if self.rangekey == '':
            return Item(self, self.data[kwargs[self.hashkey]])
        else:
            if kwargs[self.rangekey] not in self.data[kwargs[self.hashkey]]:
                raise ItemNotFound()
            return Item(
                self,
                self.data[kwargs[self.hashkey]][kwargs[self.rangekey]])

    def _remove_item(self, item):
        if item[self.hashkey] not in self.data:
            raise ItemNotFound()
        if self.rangekey == '':
            del self.data[item[self.hashkey]]
        else:
            if item[self.rangekey] not in self.data[item[self.hashkey]]:
                raise ItemNotFound()
            del self.data[item[self.hashkey]][item[self.rangekey]]

    def batch_write(self):
        return BatchTable(self)

    def query_2(self, limit=None, index=None, reverse=False,
                consistent=False, attributes=None, max_page_size=None,
                query_filter=None, conditional_operator=None,
                **filter_kwargs):
        hash_value = None
        range_value = None
        filters = []
        for key in filter_kwargs:
            meta = key.split('__')
            field_name = meta[0]
            if field_name == self.hashkey:
                operator = meta[1]
                if operator != 'eq':
                    raise Exception(
                        'Only eq operator is allowed for the hash key'
                    )
                hash_value = filter_kwargs[key]
                filters.append((self.hashkey, 'eq', hash_value))
            elif field_name == self.rangekey:
                operator = meta[1]
                range_value = filter_kwargs[key]
                filters.append((self.rangekey, operator, range_value))
            elif index is not None:
                # assume secondary index is valid - don't actually check
                operator = meta[1]
                filters.append((field_name, operator, filter_kwargs[key]))
            else:
                raise Exception(
                    'Can\'t search by "%s", only hash/range keys are allowed' %
                    field_name
                )

        if hash_value is None and index is None:
            raise Exception(
                'Hash key %s is required for query to %s' % (
                    self.hashkey, self.table_name))

        if query_filter:
            for filter_key in query_filter:
                meta = filter_key.split('__')
                field_name = meta[0]
                operator = meta[1]
                value = query_filter[filter_key]
                filters.append((field_name, operator, value))

        return self.search_by_filters(filters)

    def scan(self, limit=None, segment=None, total_segments=None,
             max_page_size=None, attributes=None, conditional_operator=None,
             **filter_kwargs):
        filters = []
        for key in filter_kwargs:
            meta = key.split('__')
            field_name = meta[0]
            operator = meta[1]
            filters.append((field_name, operator, filter_kwargs[key]))
        return self.search_by_filters(filters)

    def query_count(self, **kwargs):
        return len(self.query_2(**kwargs))

    def search_by_filters(self, filters):
        results = []
        for hash_key in self.data:
            record = self.data[hash_key]
            if not self.rangekey:
                if self.test_filters(record, filters):
                    results.append(Item(self, record))
            else:
                for rng_key in record:
                    if self.test_filters(record[rng_key], filters):
                        results.append(Item(self, record[rng_key]))
        return results

    def test_filters(self, record, filters):
        for f in filters:
            field_name = f[0]
            operator = f[1]
            value = f[2]
            if field_name not in record:
                return False
            if operator not in ('eq', 'gt', 'gte', 'lt', 'lte', 'between'):
                raise Exception('Unsupported mock operator %s' % operator)
            if operator == 'eq' and not (record[field_name] == value):
                return False
            elif operator == 'gt' and not (record[field_name] > value):
                return False
            elif operator == 'gte' and not (record[field_name] >= value):
                return False
            elif operator == 'lt' and not (record[field_name] < value):
                return False
            elif operator == 'lte' and not (record[field_name] <= value):
                return False
            elif operator == 'between' and not (
                (record[field_name] < value) or (record[field_name] > value)
            ):
                return False
        return True

    def describe(self):
        result = {'Table': {
            'TableStatus': 'ACTIVE',
            'ProvisionedThroughput': {
                'WriteCapacityUnits': self.meta['throughput']['write'],
                'ReadCapacityUnits': self.meta['throughput']['read']
            },
            'GlobalSecondaryIndexes': []
        }}
        if self.meta['global_indexes']:
            for idx in self.meta['global_indexes']:
                idx_data = {
                    'IndexName': idx.name,
                    'ProvisionedThroughput': {
                        'WriteCapacityUnits': idx.throughput['write'],
                        'ReadCapacityUnits': idx.throughput['read']
                    }
                }
                result['Table']['GlobalSecondaryIndexes'].append(idx_data)

        self.schema = [HashKey(self.hashkey)]
        if self.rangekey:
            self.schema.append(RangeKey(self.rangekey))
        return result

    def update(self, throughput, global_indexes=None):
        """
        Updates table attributes.
        """
        self.meta['throughput'] = throughput
        if global_indexes:
            for gsi_name, gsi_throughput in global_indexes.items():
                for idx in self.meta['global_indexes']:
                    if idx.name == gsi_name:
                        idx.throughput = gsi_throughput
                        break

        return True

    def get_data(self, **kwargs):
        return self.data

    def _set_data(self, data):
        final_data = {}
        checker = Item(self)
        for key, value in data.items():
            if not checker._is_storable(value):
                continue
            final_data[key] = value

        if self.rangekey == '':
            self.data[final_data[self.hashkey]] = final_data
        else:
            self.data[final_data[self.hashkey]][final_data[self.rangekey]] = \
                final_data

    def update_item(self, key, attribute_updates=None,
                    expected=None, conditional_operator=None,
                    return_values=None, return_consumed_capacity=None,
                    return_item_collection_metrics=None,
                    update_expression=None, condition_expression=None,
                    expression_attribute_names=None,
                    expression_attribute_values=None):
        """Update item low-level method.
           Warning: support is very limited, only for counter updates
        """
        dyn = Dynamizer()
        # print update_expression, expression_attribute_values
        for name in key:
            key[name] = dyn.decode(key[name])
        item = self.get_item(**key)
        # expression is like SET a = a + :a SET b = b + :b'
        try:
            key, val = update_expression.split('=')[1].split('+')
        except IndexError:
            raise Exception(
                'Table.update_item is limited to counter updates, '
                'expressions like SET a = a + :val')
        key, val = key.strip(), val.strip()
        if expression_attribute_names and key in expression_attribute_names:
            key = expression_attribute_names[key]
        val = expression_attribute_values[val]
        item[dyn.decode(key)] += dyn.decode(val)
        item.save()

    def __repr__(self):
        return "'%s'" % self.table_name


class Item(dict):

    def __init__(self, table, data=None):
        self.table = table
        super(Item, self).__init__(data or {})

    def save(self, overwrite=True):
        self.table._set_data(self)

    def partial_save(self, overwrite=True):
        self.table._set_data(self)

    def prepare_partial(self):
        return None, None

    def delete(self):
        self.table._remove_item(self)

    def _is_storable(self, value):
        if not value:
            if value not in (0, 0.0, False):
                return False
        return True


class BatchTable(object):
    """
    Used by ``Table`` as the context manager for batch writes.

    You likely don't want to try to use this object directly.
    """
    def __init__(self, table):
        self.table = table
        self._to_put = []
        self._to_delete = []

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self._to_put or self._to_delete:
            # Flush anything that's left.
            self.flush()

    def put_item(self, data, overwrite=False):
        self._to_put.append(data)

        if self.should_flush():
            self.flush()

    def delete_item(self, **kwargs):
        self._to_delete.append(kwargs)

        if self.should_flush():
            self.flush()

    def should_flush(self):
        if len(self._to_put) + len(self._to_delete) == 25:
            return True

        return False

    def flush(self):
        for put in self._to_put:
            item = Item(self.table, data=put)
            item.save()

        for delete in self._to_delete:
            item.delete()

        self._to_put = []
        self._to_delete = []
        return True


# Mock real classes / functions
import boto.dynamodb2.layer1  # noqa
import boto.dynamodb2.table  # noqa
import boto.dynamodb2.items  # noqa
boto.dynamodb2.layer1.DynamoDBConnection = Connection
boto.dynamodb2.table.Table = Table
boto.dynamodb2.items.Item = Item

from dynamo_objects import database  # noqa
database.item_to_dict = mock_item_to_dict
database.Table = Table
database.Item = Item
