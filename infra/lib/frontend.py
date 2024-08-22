# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
    aws_cognito as cognito,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_actions as elbv2_actions,
    RemovalPolicy,
    CfnOutput,
)
import os

class FrontendConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, agent_id: str, agent_alias_id: str, aws_region: str, src_dir: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ECS Cluster
        cluster = ecs.Cluster(self, "CarPartsAssistantCluster", vpc=vpc)

        # Frontend Docker image
        frontend_image = ecs.ContainerImage.from_asset(
            directory=os.path.join(src_dir, 'frontend'),  # Ensure this path points to your application code with Dockerfile
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        # Fargate service
        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "CarPartsAssistantService",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=frontend_image,
                container_port=8501,
                environment={
                    "WORKLOAD_PREFIX": "Awesome Car Parts",
                    "AGENT_ID": agent_id,
                    "AGENT_ALIAS_ID": agent_alias_id,
                    "AWS_REGION": aws_region,
                },
            ),
            public_load_balancer=True,
        )

        # Grant permissions to invoke Bedrock
        self.fargate_service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeAgent",
                    "bedrock:InvokeModel"
                ],
                resources=["*"],  # You might want to restrict this to specific Bedrock resources
            )
        )

        # Outputs
        CfnOutput(self, "FrontendURL", 
                  value=f"http://{self.fargate_service.load_balancer.load_balancer_dns_name}",
                  description="URL of the Car Parts Assistant frontend")