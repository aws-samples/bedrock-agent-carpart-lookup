# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import (
    Aws,
    Token,
    aws_lambda as _lambda,
    aws_iam as iam,
    Duration,
    BundlingOptions,
    CfnOutput,
)
import os

class LambdaConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, src_dir: str, opensearch_collection, stack_name: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Consistent naming
        function_name = f"{stack_name}-car-parts-api-{construct_id.lower()}"

        # Collection Endpoint 
        collectionEndpoint = "{}.{}.aoss.{}".format(
            Token.as_string(opensearch_collection.collection_id),
            Aws.REGION,
            Aws.URL_SUFFIX,
        )

        try:
            self.lookup_function = _lambda.Function(
                self,
                "CarPartsAgentLambda",
                function_name=function_name,
                runtime=_lambda.Runtime.PYTHON_3_9,
                handler="index.lambda_handler",
                code=_lambda.Code.from_asset(
                    os.path.join(src_dir, 'backend'),
                    bundling=BundlingOptions(
                        image=_lambda.Runtime('python3.9:latest-x86_64', _lambda.RuntimeFamily.PYTHON).bundling_image,
                        command=[
                            "bash",
                            "-c",
                            "pip install --no-cache-dir -r requirements.txt -t /asset-output && cp -au . /asset-output",
                        ],
                    ),
                ),
                timeout=Duration.seconds(900),
                environment={
                    "OPENSEARCH_ENDPOINT": collectionEndpoint,
                    "COMPATIBLE_PARTS_INDEX": "compatible-parts",
                    "INVENTORY_INDEX": "inventory",
                },
            )

            # Apply least privilege principle
            opensearch_collection.grant_data_access(self.lookup_function.role)


        except Exception as e:
            print(f"Error setting up Lambda function: {str(e)}")
            raise

        # Output the Lambda function name for reference
        CfnOutput(self, "LambdaFunctionName", value=self.lookup_function.function_name, 
                  description="Name of the Lambda function for car parts lookup")
