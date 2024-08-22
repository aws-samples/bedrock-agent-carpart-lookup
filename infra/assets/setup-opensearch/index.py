# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import time

def create_aws_auth(region):
    credentials = boto3.Session(region_name=region).get_credentials()
    return AWS4Auth(credentials.access_key, credentials.secret_key,
                    region, 'aoss', session_token=credentials.token)

def create_opensearch_client(host, region):
    awsauth = create_aws_auth(region)
    return OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )

def create_index(client, index_name, mapping):
    response = client.indices.create(index=index_name, body=mapping)
    print(f'Creating index {index_name}:', response)

def add_data_to_index(client, index_name, data_array):
    for data in data_array:
        response = client.index(index=index_name, body=data)
        print(f'Adding document to {index_name}:', response)

def handler(event, context):
    print('Received event:', json.dumps(event))
    
    request_type = event['RequestType']
    if request_type == 'Create' or request_type == 'Update':
        print('Wait 120 seconds for Security Policy to be effective...')
        time.sleep(120)
        host = os.environ['OPENSEARCH_ENDPOINT']
        region = os.environ['AWS_REGION']
        index_name = event['ResourceProperties']['IndexName']
        mapping_file = event['ResourceProperties']['MappingFile']
        data_file = event['ResourceProperties']['DataFile']
        
        # Read mapping and data files from the Lambda package
        with open(mapping_file, 'r') as f:
            mapping = json.load(f)
        
        with open(data_file, 'r') as f:
            data_array = json.load(f)
        
        client = create_opensearch_client(host, region)
        
        if not client.indices.exists(index=index_name):
            create_index(client, index_name, mapping)
        add_data_to_index(client, index_name, data_array)
        
        return {
            'PhysicalResourceId': index_name,
            'Data': {
                'IndexName': index_name
            }
        }
    elif request_type == 'Delete':
        pass
    
    return {
        'PhysicalResourceId': event.get('PhysicalResourceId', 'NOT_CREATED')
    }