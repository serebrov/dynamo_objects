from boto.dynamodb2.fields import HashKey, RangeKey, GlobalAllIndex
from boto.dynamodb2.types import NUMBER, STRING
from dynamo_objects.database import DynamoTable, DynamoRecord


def normalize_tags(tags):
    """
    -- tags - string of comma-separated tags like 'one, two, three '

    Function splits tags by comma and strips each tag.
    Returns a list, like ['one', 'two', 'three']
    """
    if not tags:
        return []
    if not isinstance(tags, basestring):
        return tags
    return map(unicode.strip, tags.split(','))


class Company(DynamoRecord):

    def __init__(self, **data):
        self.company_id = ''
        self.name = ''
        super(Company, self).__init__(**data)


class CompanyTable(DynamoTable):

    def __init__(self):
        super(self.__class__, self).__init__(
            'store',
            schema=[HashKey('company_id')],
            throughput={'read': 3, 'write': 3},
            record_class=Company)

    def get_stores(self):
        return StoreTable().query(
            company_id__eq=self.company_id, index='StoreCompanyIndex')


class Store(DynamoRecord):

    def __init__(self, **data):
        self.store_id = ''
        self.company_id = ''
        self.city = ''
        self.country = ''
        self.tags = []
        super(Store, self).__init__(**data)

    def _check_data(self):
        # use _check_data to transform the data before saving to the db
        self.tags = normalize_tags(self.tags)


class StoreTable(DynamoTable):

    def __init__(self):
        super(self.__class__, self).__init__(
            'store',
            schema=[HashKey('store_id')],
            global_indexes=[
                GlobalAllIndex(
                    'StoreCompanyIndex',
                    parts=[
                        HashKey('company_id'),
                        RangeKey('store_id', data_type=STRING)
                    ],
                    throughput={'read': 3, 'write': 3}
                )
            ],
            throughput={'read': 3, 'write': 3},
            record_class=Store)


class Customer(DynamoRecord):

    def __init__(self, **data):
        self.customer_id = ''
        self.first_name = ''
        self.last_name = ''
        self.email = ''
        self.gender = ''
        self.updated = 0
        self._ts = None
        self.employee_at_store = ''
        super(Customer, self).__init__(**data)

    def check_attrs(self, data):
        # we actually go schema-less here and allow any fields
        pass

    def _check_data(self):
        if self.gender and self.gender not in ('male', 'female'):
            raise DynamoException('Unknown gender: %s' % self.gender)


class CustomerTable(DynamoTable):

    def __init__(self):
        super(CustomerTable, self).__init__(
            'customer',
            schema=[HashKey('customer_id')],
            throughput={'read': 20, 'write': 4},
            record_class=Customer)

    def save(self, record):
        ts = record._ts or dateutil.now_timestamp()
        record.updated = ts
        return super(Customer, self).save(record)


class CustomerVisit(DynamoRecord):

    def __init__(self, **data):
        self.customer_store = ''
        self.customer_id = ''
        self.store_id = ''
        super(CustomerVisit, self).__init__(**data)

    def _check_data(self):
        if self.customer_id and self.store_id:
            self.customer_store = CustomerVisit.get_hash(self.customer_id, self.store_id)

    @staticmethod
    def get_hash(customer_id, store_id):
        return '%s|%s' % (customer_id, store_id)


class CustomerVisitTable(DynamoTable):

    def __init__(self):
        super(self.__class__, self).__init__(
            'customer_visit',
            schema=[HashKey('customer_store')],
            throughput={'read': 3, 'write': 1},
            record_class=CustomerVisit)

    def get_by_hash(self, customer_id, store_id):
        customer_store = CustomerVisit.get_hash(customer_id, store_id)
        return super(CustomerVisitTable, self).get(customer_store)
