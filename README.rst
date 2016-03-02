================================
dynamo_objects
================================

.. image:: https://travis-ci.org/serebrov/dynamo_objects.png?branch=master
    :target: https://travis-ci.org/serebrov/dynamo_objects
.. image:: https://coveralls.io/repos/serebrov/dynamo_objects/badge.svg?branch=master&service=github 
    :target: https://coveralls.io/github/serebrov/dynamo_objects?branch=master
.. image:: https://img.shields.io/pypi/v/dynamo-objects.svg
    :target: https://pypi.python.org/pypi/dynamo-objects/
.. image:: https://img.shields.io/pypi/dm/dynamo-objects.svg
    :target: https://pypi.python.org/pypi/dynamo-objects/

dynamo_objects is a set of tools to work with DynamoDB in python.

It is based on `boto <http://boto.readthedocs.org/en/latest/ref/dynamodb2.html>`_ and provides following features:

* a simple object mapper - use object notation to work with dynamo records
* new tables are automatically created in the database, so you just write 
  and deploy the new code
* transparent support for table prefixes (multiple databases or multiple environments), you don't need to handle table prefixes in code, just set the prefix during the database connection
* simple in-memory dynamodb mock for fast unit tests
* supports `DynamoDB local <https://aws.amazon.com/blogs/aws/dynamodb-local-for-desktop-development/>`_ for slower tests
* in-memory cached tables to speedup computational operations on top of DynamoDB - all data is read only once and then results are flushed back in a batch
* additional tools - copy data from table to table, a context manager to update table throughputs and set back once operation is completed

`Discussion group <https://groups.google.com/forum/#!forum/dynamo_objects>`_

================================
Installation
================================

.. code-block:: bash

    $ pip install dynamo_objects


================================
DB Connection and Table Prefixes
================================

Database connection method adds table prefix support on top of boto's connect_to_region method.
Using the table prefix it is possible to switch the application to different set of tables for different environments (or just use different prefixes for different applications).

Use the following snippet to connect to the database:

.. code-block:: python

    from dynamo_objects import DynamoDatabase

    DynamoDatabase().connect(
        region_name='your-aws-region-name-here',
        aws_access_key_id='access-key-id',
        aws_secret_access_key='secret-access-key',
        table_prefix='my_prefix_')

Region name, and aws credentials are passed to the boto's connect_to_region method, so you can use other ways `suppored by boto <http://boto.readthedocs.org/en/latest/boto_config_tut.html#credentials>`_ to specify aws credentials.
For example, it is not necessary to specify access key id and secret if you use IAM role.

The :code:`table_prefix` parameter is used to prefix all the table names with the string you specify.

Like if you set the table_prefix to :code:`staging_`, the application will use tables like :code:`staging_user` and :code:`staging_post`. And if you set the prefix to :code:`dev_` then application will use :code:`dev_user`, :code:`dev_post`.

If you leave the table_prefix empty then it will be just :code:`user` and :code:`post`.
This way you can easily switch your application from one set of tables to another for different environments (development, staging, production).

To connect to the DynamoDB Local, specify the region_name='localhost':

.. code-block:: python

    from dynamo_objects import DynamoDatabase
    DynamoDatabase().connect(
        region_name='localhost',
        table_prefix='dev_'
    )

================================
Object Mapper
================================

To use the object mapper, define record and table objects for each DynamoDB table:

.. code-block:: python

  from boto.dynamodb2.fields import HashKey, RangeKey
  from dynamo_objects import DynamoRecord, DynamoTable

  class Store(DynamoRecord):

      def __init__(self, **data):
          # define table fields in the __init__ method
          self.store_id = ''
          self.name = ''
          self.tags = []
          super(Store, self).__init__(**data)


  class StoreTable(DynamoTable):

      def __init__(self):
          super(self.__class__, self).__init__(
              'store',
              schema=[HashKey('store_id')],
              throughput={'read': 3, 'write': 3},
              record_class=Store)

Here the :code:`StoreTable` class describes the table: table name, schema (hash and optionally range keys), throughput and record class.

And the :code:`Store` class describes the table row, 
in the :code:`__init__` method we put all the table fields.

See more examples of table/record objects in the `tests/schema.py <https://github.com/dynamo_objects/blob/master/tests/schema.py>`_ file.

Now the record object can be created and used like this:

.. code-block:: python

    store = StoreTable()
    store = Store()
    store.name = 'My Store'
    table.save(store)

    # or initialize the fields using the constructor
    store2 = Store(name='My Store 2')
    # change the name
    store2.name = 'Another Store'
    StoreTable().save(store)

Compare this to the pure boto code where you have a dictionary-like interface:

.. code-block:: python

    store = Item(stores, data={
       name='My Store'
    })
    # ....
    store['nmae'] = 'Another Store'

If you mistype the field name like in :code:`store['nmae']` there will be no error - you will just create a new field in the database.
The main purpose of the object mapper is to prevent this. 

The :code:`DynamoRecord` object will raise an exception if you mistype the field name.
To actually go schema-less, it is possible to override the :code:`_freeze_schema` method with :code:`pass` in the method body.

You can also override the :code:`_check_data` method to do additional transformations before saving to the database (like convert data types or normalize/unify data format).

Find a record, update it and save:

.. code-block:: python

    table = MyTable()
    # will raise ItemNotFound exception if record does not exist
    record = table.get('my_hash', 'my_range')
    record.some_field = 100
    table.save(record)

    # to handle the case when there is no record int the database use
    # try/except
    from boto.dynamodb2.exceptions import ItemNotFound
    try:
        record = table.get('my_hash', 'my_range')
    except ItemNotFound:
        # handle the record not found case
        # ...

    # sometimes it is more convenient to get None for non-existing record
    # `find` method will return None if record does not exist
    record = table.find('my_hash', 'my_range')
    if record is not None:
        record.some_field = 100
        table.save(record)

    # get a record or create new one if record does not exist
    record = table.get('my_hash', 'my_range', create=True)
    record.some_field = 200
    table.save(record)

    # delete the existing record
    # `delete` method will return the deleted record, so the record data can be
    # used for some additional actions like logging
    record = table.delete('hash', 'range')

The :code:`create=True` option for the :code:`table.get()` method is useful when you want to read the data from the database or get the Null object if data is not found.
For example:

.. code-block:: python

    class User(DynamoRecord):

      def __init__(self, *data):
         self.name = 'guest'
         self.password = ''
         super(User, self).__init__(**data)

    # Find the user in the database, if not found - the `user` object 
    # will represent guest user
    user = table.get(user_id, create=True)
    # print user name or 'guest' (default)
    print user.name

Query and scan methods have the same interface as boto's `query_2 <http://boto.readthedocs.org/en/latest/ref/dynamodb2.html#boto.dynamodb2.table.Table.query_2>`_ and `scan <http://boto.readthedocs.org/en/latest/ref/dynamodb2.html#boto.dynamodb2.table.Table.scan>`_, but will convert the resulting record set into :code:`DynamoRecord` objects.

.. code-block:: python

    # parameters are the same as for boto's query_2
    # returns array of records
    # don't use when you expect a lot of data, because it will
    # fetch all the data from the database and convert to DynamoRecord
    # before returning
    records = table.query(hash__eq='value', range__gte=50)
    ...
    records = table.scan(some_field__gte=10)
    ...
    # get count
    count = table.query_count(hash__eq='value', range__gte=50)

Table object also supports the atomic counter update: 

.. code-block:: python

    # increment the `counter_name` field by 2 for the 
    # item with hash key = `myhashkey`
    table.update_counter('myhashkey', counter_name=2)

    # decrement the `counter_name` field by 2 for the 
    # item with hash key = `myhashkey` and rangekey = 'myrange'
    table.update_counter('myhashkey', 'myrange', counter_name=-2)

And it is possible to use boto's objects directly:

.. code-block:: python

    table = MyTable()
    # the boto Table object
    boto_table = table.table
    # ... 

    record = table.get('my_hash', 'my_range')
    # the boto Item object
    boto_item = record._item
    # ... 


================================
Memory tables
================================

Memory tables can be used to cache DynamoDB access in-memory.
Every record is only read once and no data is written until you call the :code:`save_data` or :code:`save_data_batch` method.

.. code-block:: python

  # StoreTable is a regular table definition, DynamoTable subclass
  from myschema import StoreTable
  from dynamo_objects.memorydb import MemoryTable

  class StoreMemoryTable(MemoryTable):

      def __init__(self):
          super(StoreMemoryTable, self).__init__(StoreTable())

Here we define a :code:`StoreMemoryTable` class for in-memory table which wraps the :code:`StoreTable` (a regular table definition).
Now we can do this:


.. code-block:: python

    table = StoreMemoryTable()
    # read records with store_id = 1 and store_id = 2
    record = table.get(1)
    record2 = table.get(2)
    # data is not actually saved yet, no write db operations
    table.save(record)
    table.save(record2)
    # ...
    # read same records again - will fetch from memory, no db read operations
    record = table.get(1)
    record2 = table.get(2)
    # ...
    # data is not actually saved yet, no write db operations
    table.save(record)
    table.save(record2)
    # Now we flush all the data back to DynamoDB
    # the `save_data_batch` will use the `batch write` DynamoDB operation
    table.save_data_batch()

This can be very useful if you do some computational operations and need to read / write a lot of small objects to the database.
Depending on the data structure the used read / write throughput and the whole processing time can be noticeably reduced.

================================
Testing and DynamoDB Mock
================================

It is possible to run unit tests using the real DynamoDB connection using the table prefixes feature: you can choose some special table prefix like :code:`xx_unit_tests_`. 
This way you'll have a set of tables for your unit tests.

But this approach is not practical - tests will be slow and will consume the read/write operations (and this will cost money).

Amazon provides a `DynamoDB emulator in java <https://aws.amazon.com/blogs/aws/dynamodb-local-for-desktop-development/>`_ but it is problematic to use it during development, because it is slow and consumes a lot of memory.

The solution is a simple in-memory `DynamoDB mock module <https://github.com/dynamo_objects/blob/master/dynamo_objects/dynamock.py>`_. 
It is a fast, but very approximate dynamo emulation without permanent data storage.

To enable the mock, just import the :code:`dynamock` module:

.. code-block:: python

  from dynamo_objects import database
  # once imported, the `dynamock` module will mock real DynamoDB
  # operations and forward them to the simple implementation which 
  # keeps all the data in memory
  from dynamo_objects import dynamock

There is an example of the mock usage in the `tests/base.py <https://github.com/dynamo_objects/blob/master/tests/base.py>`_ module.

This base test module can be used for any project to test parts of code which work with DynamoDB.
You can find examples of unit tests under the `tests <https://github.com/dynamo_objects/tree/master/tests/>`_ folder. The database schema is described in the `tests/schema.py <https://github.com/dynamo_objects/blob/master/tests/schema.py>`_.

To run all tests use :code:`nosetests` (install with :code:`pip install nose`):

.. code-block:: bash

    nosetests

By default it will use the in-memory `DynamoDB mock <https://github.com/dynamo_objects/blob/master/dynamo_objects/dynamock.py>`_. 
To run tests against the  DynamoDB Local use following commands:

.. code-block:: bash

    # in the first terminal window launch the local dynamodb
    # script will download it if necessary
    ./tool/dynamodb-local.sh

    # in another terminal window run the tests
    DYNAMODB_MOCK= nosetests

I use fast in-memory mock to run tests locally, during the development.

On the CI server tests a launched two times - first against the in-memory mock and then one more time against the DynamoDB local.

Here is an example of the shell script to do this:

.. code-block:: bash

  # Run fast tests with in-memory mock
  nosetests
  RESULT_MOCK=$?
  
  # Run slow tests with DynamoDB local
  pushd path/to/folder/with/dynamodb-local
    java -Djava.library.path=./DynamoDBLocal_lib -jar ./DynamoDBLocal.jar -inMemory -sharedDb &
    PID=$!
  popd
  echo "Started local dynamodb: $PID"
  DYNAMODB_MOCK= nosetests
  RESULT_LOCALDB=$?
  kill -9 $PID
  exit $(($RESULT_MOCK+$RESULT_LOCALDB))


================================
Additional Tools
================================

The `database <https://github.com/dynamo_objects/blob/master/dynamo_objects/database.py>`_ module contains few additional useful tools.

The :code:`copy_item` and :code:`copy_table_data` methods allow to copy data from table to table (for example, you may want to copy some data from staging to production):

.. code-block:: python

    db = database.Database()
    # note: table_prefix is empty, so we can explicitly set table names
    database.connect(
        region_name='...', ...
        table_prefix='')
    num_copied = db.copy_table_data('table_name', 'staging_table_name')

    # copy and transform data
    def transform_fn(record):
        record.name = 'staging_' + record.name
    db.copy_table_data('table_name', 'staging_table_name', transform=transform_fn)

There are also some other useful methods to create the table, wait until the new table becomes active, delete the table, etc.

The :code:`TableThroughput` class is a context manager to update (usually set higher) throughput limits and put them back after some operation.
It is useful when you need to do something what requires a high read/write throughput. 

Using the :code:`TableThroughput` it is possible to set high limits just before the operation and set them back just after it:

.. code-block:: python

        high_throughputs = {
            'table_one': { 'table': { 'read': 100, 'write': 50, }, },
            'table_two': {
                'table': { 'read': 60, 'write': 120, },
                'SomeGlobalIndex': { 'read': 1, 'write': 120 }
            }
        }

        with database.TablesThroughput(high_throughputs):
            # now throughputs are high
            some_comutational_operation()
        # now throughputs are low again (same as before the operation)


================================
Related projects
================================

* `flywheel <https://github.com/mathcamp/flywheel>`_ - Object mapper for Amazon's DynamoDB
* `PynamoDB <https://github.com/jlafon/PynamoDB>`_ - A pythonic interface to Amazon's DynamoDB
* `Dynamodb-mapper <https://bitbucket.org/Ludia/dynamodb-mapper/overview>`_ Dynamodb-mapper - a DynamoDB object mapper, based on boto
