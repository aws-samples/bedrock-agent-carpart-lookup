# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import (
    aws_s3 as s3,
    Aws,Token,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
    CfnOutput,
)
import os

class StorageConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, asset_dir: str, stack_name: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Consistent naming
        manuals_bucket_name = f"car-manuals-{Token.as_string(Aws.ACCOUNT_ID)}-{Token.as_string(Aws.REGION)}"

        # Create S3 buckets with consistent naming and enhanced security
        self.manuals_bucket = s3.Bucket(
            self,
            "Manuals",
            bucket_name=manuals_bucket_name,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # Deploy assets with error handling
        try:
            s3deploy.BucketDeployment(
                self,
                "DeployManuals",
                sources=[s3deploy.Source.asset(os.path.join(asset_dir, "owners-manuals"))],
                destination_bucket=self.manuals_bucket,
                memory_limit=1024,
                retain_on_delete=False,  # Ensure cleanup on stack deletion
            )

        except Exception as e:
            print(f"Error deploying assets: {str(e)}")
            raise

        # Output the bucket names for reference
        CfnOutput(self, "ManualsBucketName", value=self.manuals_bucket.bucket_name, 
                  description="Name of the S3 bucket containing car manuals")