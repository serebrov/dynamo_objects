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

Tests structure and description.

Run tests with in-memory mock.

./tool/test.py

Run tests with DynamoDB local

./tool/dynamodb-local.sh

DYNAMODB_MOCK= ./test.py

I use fast in-memory mock to run tests locally, during the development.
On the CI server tests a launched two times - first against the in-memory mock and then one more time against the DynamoDB local.

Here is a shell script example to to this:

.. code:: bash
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
