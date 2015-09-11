#!/usr/bin/env bash
set -e

SCRIPT_PATH=`dirname $0`
DYNAMODB_LOCAL_DIR=$SCRIPT_PATH/dynamodb_local

IN_MEMORY="true"

if ls $DYNAMODB_LOCAL_DIR/DynamoDBLocal.jar; then
    echo "Found dynamodb local, skip install"
else
    echo "Downloading dynamodb local"
    mkdir -p $DYNAMODB_LOCAL_DIR
    echo $DYNAMODB_LOCAL_DIR
    pushd $DYNAMODB_LOCAL_DIR
    wget http://dynamodb-local.s3-website-us-west-2.amazonaws.com/dynamodb_local_latest.zip
    unzip dynamodb_local_latest.zip
    popd
fi

echo "Starting DynamoDB local"
if [[ $IN_MEMORY != "true" ]]; then
  java -Djava.library.path=$DYNAMODB_LOCAL_DIR/DynamoDBLocal_lib -jar $DYNAMODB_LOCAL_DIR/DynamoDBLocal.jar -sharedDb
else
  java -Djava.library.path=$DYNAMODB_LOCAL_DIR/DynamoDBLocal_lib -jar $DYNAMODB_LOCAL_DIR/DynamoDBLocal.jar -inMemory -sharedDb
fi
