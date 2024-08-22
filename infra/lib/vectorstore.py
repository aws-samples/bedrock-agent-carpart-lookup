# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import (
    Aws,
    Duration,
    Token,
    aws_lambda as _lambda,
    aws_iam as iam,
    custom_resources as cr,
    CustomResource,
    BundlingOptions,
    CfnOutput,
)
from cdklabs.generative_ai_cdk_constructs import (
    opensearchserverless,
    opensearch_vectorindex,
)
import os


class OpenSearchConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, asset_dir: str, stack_name: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Consistent naming
        collection_name = "car-parts-collection"
        index_name = "car-manuals"

        try:
            self.collection = opensearchserverless.VectorCollection(
                self,
                "Collection",
                collection_name=collection_name,
                standby_replicas=opensearchserverless.VectorCollectionStandbyReplicas.DISABLED,
            )

            collectionEndpoint = "{}.{}.aoss.{}".format(
                Token.as_string(self.collection.collection_id),
                Aws.REGION,
                Aws.URL_SUFFIX,
            )

            self.vector_index = opensearch_vectorindex.VectorIndex(
                self,
                "VectorIndex",
                collection=self.collection,
                index_name=index_name,
                vector_dimensions=1024,
                vector_field="AMAZON_BEDROCK_TEXT_VECTOR",
                mappings=[
                    opensearch_vectorindex.MetadataManagementFieldProps(
                        mapping_field="AMAZON_BEDROCK_TEXT_CHUNK",
                        data_type="text",
                        filterable=True,
                    ),
                    opensearch_vectorindex.MetadataManagementFieldProps(
                        mapping_field="AMAZON_BEDROCK_METADATA",
                        data_type="text",
                        filterable=True,
                    ),
                ],
            )

            self.opensearch_setup_lambda = _lambda.Function(
                self,
                "OpenSearchSetupLambda",
                function_name=f"{stack_name}-opensearch-setup-{construct_id.lower()}",
                runtime=_lambda.Runtime.PYTHON_3_12,
                handler="index.handler",
                timeout=Duration.seconds(900),
                code=_lambda.Code.from_asset(
                    os.path.join(asset_dir, 'setup-opensearch'),
                    bundling=BundlingOptions(
                        image=_lambda.Runtime(
                            'python3.9:latest-x86_64', _lambda.RuntimeFamily.PYTHON).bundling_image,
                        command=[
                            "bash",
                            "-c",
                            "pip install --no-cache-dir -r requirements.txt -t /asset-output && cp -au . /asset-output",
                        ],
                    ),
                ),
                environment={
                    "OPENSEARCH_ENDPOINT": collectionEndpoint
                },
            )

            # Apply least privilege principle
            self.collection.grant_data_access(self.opensearch_setup_lambda.role)

            compatible_parts_provider = cr.Provider(
                self, "CompatiblePartsProvider", on_event_handler=self.opensearch_setup_lambda
            )

            CustomResource(
                self,
                "CompatiblePartsIndex",
                service_token=compatible_parts_provider.service_token,
                properties={
                    "IndexName": "compatible-parts",
                    "MappingFile": "./compatible-parts-index/schema.json",
                    "DataFile": "./compatible-parts-index/preload.json",
                },
            )

            inventory_provider = cr.Provider(
                self, "InventoryProvider", on_event_handler=self.opensearch_setup_lambda
            )

            CustomResource(
                self,
                "InventoryIndex",
                service_token=inventory_provider.service_token,
                properties={
                    "IndexName": "inventory",
                    "MappingFile": "./inventory-index/schema.json",
                    "DataFile": "./inventory-index/preload.json",
                },
            )

        except Exception as e:
            print(f"Error setting up OpenSearch: {str(e)}")
            raise

        # Output the OpenSearch endpoint for reference
        CfnOutput(self, "OpenSearchEndpoint", value=collectionEndpoint,
                  description="Endpoint of the OpenSearch collection")
