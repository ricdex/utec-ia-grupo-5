#!/usr/bin/env python3
"""
CDK App for FinAdvisor
Instantiates the main stack
"""

import aws_cdk as cdk
from cdk_stack import FinAdvisorStack

app = cdk.App()

FinAdvisorStack(
    app,
    "FinAdvisorStack6",
    description="FinAdvisor - AI-Powered Financial Advisory Agent on AWS",
    env=cdk.Environment(
        account=cdk.Aws.ACCOUNT_ID,
        region=cdk.Aws.REGION,
    ),
)

app.synth()
