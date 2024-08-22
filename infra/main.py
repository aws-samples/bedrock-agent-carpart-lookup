# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from cdk_nag import AwsSolutionsChecks, NagReportLogger, NagReportFormat

from constructs import Construct
from aws_cdk import Stack, App, Aspects
from aws_cdk import aws_ec2 as ec2

from lib.storage import StorageConstruct
from lib.vectorstore import OpenSearchConstruct
from lib.api import LambdaConstruct
from lib.bedrock import BedrockConstruct
from lib.frontend import FrontendConstruct
from lib.suppressions import add_suppressions

class CarPartsAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Get path of current script's parent directory
        current_dir = os.path.dirname(__file__)
        # Asset Directory
        asset_dir = os.path.join(current_dir, "assets")
        # Parent Directory
        parent_dir = os.path.dirname(current_dir)
        # Source Directory
        src_dir = os.path.join(parent_dir, "src")

        # Create VPC
        vpc = ec2.Vpc(self, "CarPartsAssistantVPC", max_azs=2)

        # Create Storage Construct
        storage = StorageConstruct(self, "Storage", asset_dir=asset_dir, stack_name=self.stack_name)

        # Create OpenSearch Construct
        opensearch = OpenSearchConstruct(self, "OpenSearch", asset_dir=asset_dir, stack_name=self.stack_name)

        # Create Lambda Construct
        api = LambdaConstruct(self, "API", src_dir=src_dir, opensearch_collection=opensearch.collection, stack_name=self.stack_name)

        # Create Bedrock Construct
        bedrock = BedrockConstruct(self, "Bedrock", 
                                   opensearch_collection=opensearch.collection, 
                                   vector_index=opensearch.vector_index, 
                                   manuals_bucket=storage.manuals_bucket,
                                   lookup_function=api.lookup_function,
                                   src_dir=src_dir
                                )

        # Create Frontend Construct
        frontend = FrontendConstruct(self, "Frontend",
                                     vpc=vpc,
                                     agent_id=bedrock.agent.agent_id,
                                     agent_alias_id=bedrock.agent.alias_id,
                                     aws_region=self.region,
                                     src_dir=src_dir)

        # Add suppressions
        add_suppressions(self)

app = App()
stack = CarPartsAgentStack(app, "CarPartsAgentStack")

# Adding CDK Nag Checks
Aspects.of(app).add(AwsSolutionsChecks(report_formats=[NagReportFormat.CSV]))

app.synth()