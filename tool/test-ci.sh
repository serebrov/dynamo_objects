#!/usr/bin/env bash
set -e

SCRIPT_PATH=`dirname $0`

cd $SCRIPT_PATH/..

# Run fast tests with in-memory mock
tox
RESULT_MOCK=$?

# Run slow tests with DynamoDB local
source ./tool/dynamodb-install.sh
pushd tool/dynamodb_local
  java -Djava.library.path=./DynamoDBLocal_lib -jar ./DynamoDBLocal.jar -inMemory -sharedDb &
  PID=$!
popd
echo "Started local dynamodb: $PID"
DYNAMODB_MOCK= tox
RESULT_LOCALDB=$?
#kill -9 $PID
exit $(($RESULT_MOCK+$RESULT_LOCALDB))
