#!/usr/bin/env bash
set -e

SCRIPT_PATH=`dirname $0`
DYNAMODB_LOCAL_DIR=$SCRIPT_PATH/dynamodb_local

IN_MEMORY="true"

source $SCRIPT_PATH/dynamodb-install.sh

echo "Starting DynamoDB local"
if [[ $IN_MEMORY != "true" ]]; then
  java -Djava.library.path=$DYNAMODB_LOCAL_DIR/DynamoDBLocal_lib -jar $DYNAMODB_LOCAL_DIR/DynamoDBLocal.jar -sharedDb
else
  java -Djava.library.path=$DYNAMODB_LOCAL_DIR/DynamoDBLocal_lib -jar $DYNAMODB_LOCAL_DIR/DynamoDBLocal.jar -inMemory -sharedDb
fi
