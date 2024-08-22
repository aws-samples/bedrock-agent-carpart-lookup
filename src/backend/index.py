# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import BedrockAgentResolver
from aws_lambda_powertools.event_handler.openapi.params import Body, Query
from aws_lambda_powertools.utilities.typing import LambdaContext

from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

import boto3

tracer = Tracer()
logger = Logger()
app = BedrockAgentResolver()

# Updated Pydantic models for input validation
class PartFromInventoryRequest(BaseModel):
    part_ids: Union[str, List[str]] = Field(..., description="A single part ID or a list of part IDs to retrieve detailed information of the part from the inventory. Example: '76622-T0A-A01' or ['76622-T0A-A01', '76630-T0A-A01']")

class CompatiblePartsRequest(BaseModel):
    make: str = Field(..., description="Make of the vehicle. Example: 'Honda'")
    model: str = Field(..., description="Model of the vehicle. Example: 'CR-V'")
    year: int = Field(..., description="Year of the vehicle. Example: 2021")
    category: Optional[str] = Field(None, description="Category of the part. This field is optional but highly recommended for more accurate and relevant results. Example: 'Wipers' or 'Wiper Blades'")

def get_search_client():
    logger.info("Initializing search client")
    region = os.environ['AWS_REGION']
    host = os.environ['OPENSEARCH_ENDPOINT']
    service = 'aoss'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    logger.info("OpenSearch client initialized successfully")
    return client

@app.post("/get_part_from_inventory", description="Get part information from the inventory based on part ID(s).")
@tracer.capture_method
def get_part_from_inventory(
    request: Annotated[PartFromInventoryRequest, Body(description="Part ID(s) to retrieve from the inventory.")]
) -> Dict:
    logger.info("Received request to get part(s) from inventory", extra={"request": request.model_dump_json()})
    client = get_search_client()
    index_name = os.environ.get('INVENTORY_INDEX' , "inventory")

    # Convert single part_id to list if necessary
    part_ids = request.part_ids if isinstance(request.part_ids, list) else [request.part_ids]

    search_query = {
        "query": {
            "terms": {
                "part_number": part_ids
            }
        }
    }
    
    logger.info("Constructed search query", extra={"query": search_query})

    try:
        logger.info(f"Executing search on index '{index_name}'")
        results = client.search(index=index_name, body=search_query)
        logger.info(f"Search completed successfully. Found {results['hits']['total']['value']} results.")
        return {"results": results['hits']['hits']}
    except Exception as e:
        logger.info(f"Error searching inventory: {str(e)}")
        raise

@app.post("/get_compatible_parts", description="Get parts that are compatible with a specific vehicle make, model, and year. Using the category field is highly recommended for more accurate and relevant results.")
@tracer.capture_method
def get_compatible_parts(
    request: Annotated[CompatiblePartsRequest, Body(description="Vehicle information to find compatible parts. The category field is optional but highly recommended for more accurate and relevant results.")]
) -> Dict:
    logger.info("Received request to get compatible parts", extra={"request": request.dict()})
    client = get_search_client()
    index_name = os.environ.get('COMPATIBLE_PARTS_INDEX' , "compatible-parts")

    must_conditions = [
        {"match": {"make": request.make}},
        {"match": {"model": request.model}},
        {"term": {"years": request.year}}
    ]
    
    if request.category:
        must_conditions.append({
            "multi_match": {
                "query": request.category,
                "fields": ["category", "parts.part_name"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        })

    search_query = {
        "query": {
            "bool": {
                "must": must_conditions
            }
        }
    }
    
    logger.info("Constructed search query", extra={"query": search_query})

    try:
        logger.info(f"Executing search on index '{index_name}'")
        results = client.search(index=index_name, body=search_query)
        logger.info(f"Search completed successfully. Found {results['hits']['total']['value']} results.")
        return {"results": results['hits']['hits']}
    except Exception as e:
        logger.info(f"Error searching compatible parts: {str(e)}")
        raise

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Lambda function invoked", extra={"event": event})
    try:
        result = app.resolve(event, context)
        logger.info("Lambda function completed successfully")
        return result
    except Exception as e:
        logger.info(f"Lambda function encountered an error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

if __name__ == "__main__":
    print(app.get_openapi_json_schema(
        title="Car Parts Inventory API",
        version="1.0.0",
        description="This API provides endpoints for querying car parts inventory and compatibility information. Use the get_part_from_inventory endpoint to retrieve specific parts from the inventory by their IDs, and the get_compatible_parts endpoint to find parts compatible with specific vehicles. For get_compatible_parts, the category field is optional but highly recommended for more accurate and relevant results."
    ))