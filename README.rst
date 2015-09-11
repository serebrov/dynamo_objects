========
dynamo_objects
========

dynamo_objects is a set of tools to work with DynamoDB in python.

It is based on `boto <http://boto.readthedocs.org/en/latest/ref/dynamodb2.html>`_ and provides following features:

* a simple object mapper - use object notation to work with dynamo records
* new tables are automatically created in the database, so you just write 
  the new code and deploy to the server and tables are added automatically
* transparent support for table prefixes (multiple databases or multiple environments), you don't need to handle table prefixes in code, just set the prefix during the database connection
* simple in-memory dynamodb mock for fast unit tests
* supports `DynamoDB local <https://aws.amazon.com/blogs/aws/dynamodb-local-for-desktop-development/>`_ for slower tests
* in-memory cached tables to speedup computational operations on top of DynamoDB - all data is read only once and then results are flushed back in a batch
* additional tools - copy data from table to table, a context manager to update table throughputs and set back once operation is completed

`Discussion group <https://groups.google.com/forum/#!forum/dynamo_objects>`_

========
DB Connection and Table Perfixes
========

========
Object Mapper
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

========
Related projects
========

* `flywheel <https://github.com/mathcamp/flywheel>`_ - Object mapper for Amazon's DynamoDB)
* `PynamoDB <https://github.com/jlafon/PynamoDB>`_ - A pythonic interface to Amazon's DynamoDB
* `Dynamodb-mapper <https://bitbucket.org/Ludia/dynamodb-mapper/overview>`_ Dynamodb-mapper - a DynamoDB object mapper, based on boto
