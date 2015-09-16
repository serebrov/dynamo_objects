========
dynamo_objects
========

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

========
DB Connection and Table Perfixes
========

Use the following snippet to connect to the database:

.. code-block:: python

    from dynamo_objects import database

    database.Database().connect(
        region_name='your-aws-region-name-here',
        aws_access_key_id='access-key-id',
        aws_secret_access_key='secret-access-key',
        table_prefix='my_prefix_')

Region name, and aws credentials are passed to the boto's connect_to_region method, so you can use other ways `suppored by boto <http://boto.readthedocs.org/en/latest/boto_config_tut.html#credentials>`_ to specify aws credentials.
For example, it is not necessary to specify access key id and secret if you use IAM role.

The `table_prefix` parameter is used to prefix all the table names with the string you specify.
Like if you set the table_prefix to `staging_`, the application will use tables like `staging_user` and `staging_post`. And if you set the prefix to `dev_` then application will use `dev_user`, 'dev_post`.
If you leave the table_prefix empty then it will be just `user` and `post`.
This way you can easily switch your application from one set of tables to another for different environments (development, staging, production).

To connect to the DynamoDB Local, specify the region_name='localhost':

.. code-block:: python

        database.Database().connect(
            region_name='localhost',
            table_prefix='dev_'
        )

========
Object Mapper
========

To use the object mapper, define record and table objects for each DynamoDB table:

.. code-block:: python

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

Here the `StoreTable` class describes the table: table name, schema (hash and optionally range keys), throughput and record class.

And the `Store` class describes the table row, 
in the :code:`__init__` method we put all the table fields.

See more examples of table/record objects in the `tests/schema.py <tests/schema.py>`_ file.

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

Compare this to pure boto where you have a dictionary-like interface:

.. code-block:: python
    store = Item(stores, data={
       name='My Store'
    })
    # ....
    store['nmae'] = 'Another Store'

If you mistype the field name like in `store['nmae']` there will be no error - you will just create a new field in the database.
The main purpose of the object mapper is to prevent this. 

The `DynamoRecord` object will raise an exception if you mistype the field name.
To actually go schema-less, it is possible to override the `_freeze_schema` method with `pass` in the method body.

You can also override the `_check_data` method to do additional transformations before saving to the database (like convert data types or normalize/unify data format).

========
Memory tables
========

Memory tables can be used to cache DynamoDB access in-memory.
Every record is only read once and no data is written until you call the `batch_write` method.

========
DynamoDB Mock
========

========
Testing
========

While it is possible to run unit tests using the real DynamoDB connection, using the table prefixes feature you can choose some special table prefix like `xx_unit_tests_`. 
This way you'll have a set of tables for your unit tests.
But it is not practical - tests will be slow and will consume the read/write operations (and this will cost money).

Amazon provides a `DynamoDB emulator in java <https://aws.amazon.com/blogs/aws/dynamodb-local-for-desktop-development/>`_ but it is problematic to use it during development, because it is slow and consumes a lot of memory.

The solution is a simple in-memory `DynamoDB mock module <dynamo_objects/dynamock.py>`_. 
It is a fast, but very approximate dynamo emulation without permanent data storage.

You can find examples of unit tests under the `tests <tests/>`_ folder. The database schema is described in the `tests/schema.py <tests/schema.py>`_.
The same structure and approach can be used to write unit tests for your project.

There is a helper `test.py <tools/test.py>`_ script to run all unit tests:

.. code-block:: bash

    ./tool/test.py

By default it will use the in-memory `DynamoDB mock <dynamo_objects/dynamock.py>`_. 
To run tests against the  DynamoDB Local use following commands:

.. code-block:: bash

    # in the first terminal window launch the local dynamodb
    # script will download it if necessary
    ./tool/dynamodb-local.sh

    # in another terminal window run the tests
    DYNAMODB_MOCK= ./test.py

I use fast in-memory mock to run tests locally, during the development.

On the CI server tests a launched two times - first against the in-memory mock and then one more time against the DynamoDB local.

Here is a shell script example to to this:

.. code-block:: bash

  # Run fast tests with in-memory mock
  python -m unittest discover -s tests
  RESULT_MOCK=$?
  
  # Run slow tests with DynamoDB local
  pushd paty/to/folder/with/dynamodb-local
    java -Djava.library.path=./DynamoDBLocal_lib -jar ./DynamoDBLocal.jar -inMemory -sharedDb &
    PID=$!
  popd
  echo "Started local dynamodb: $PID"
  DYNAMODB_MOCK= python -m unittest discover -s tests
  RESULT_LOCALDB=$?
  kill -9 $PID
  exit $(($RESULT_MOCK+$RESULT_LOCALDB))


========
Additional Tools
========

DB - copy table

========
Related projects
========

* `flywheel <https://github.com/mathcamp/flywheel>`_ - Object mapper for Amazon's DynamoDB)
* `PynamoDB <https://github.com/jlafon/PynamoDB>`_ - A pythonic interface to Amazon's DynamoDB
* `Dynamodb-mapper <https://bitbucket.org/Ludia/dynamodb-mapper/overview>`_ Dynamodb-mapper - a DynamoDB object mapper, based on boto
