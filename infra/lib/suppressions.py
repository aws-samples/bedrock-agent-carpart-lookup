# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from cdk_nag import NagSuppressions

def add_suppressions(stack):
    NagSuppressions.add_stack_suppressions(stack, [
        {"id": "AwsSolutions-VPC7", "reason": "VPC Flow Logs are not required for this demo"},
        {"id": "AwsSolutions-S1", "reason": "Server access logs are not required for this demo bucket"},
        {"id": "AwsSolutions-IAM4", "reason": "Using AWS managed policies is acceptable for this demo"},
        {"id": "AwsSolutions-IAM5", "reason": "Wildcard permissions are acceptable for this demo"},
        {"id": "AwsSolutions-L1", "reason": "Latest runtime version not required for this demo"},
        {"id": "AwsSolutions-ECS4", "reason": "CloudWatch Container Insights not required for this demo"},
        {"id": "AwsSolutions-ELB2", "reason": "ELB access logs not required for this demo"},
        {"id": "AwsSolutions-EC23", "reason": "Open inbound access is acceptable for this demo"},
        {"id": "AwsSolutions-ECS2", "reason": "Direct environment variable specification is acceptable for this demo"},
        {"id": "CdkNagValidationFailure", "reason": "Suppressing validation failures for this demo"},
    ])