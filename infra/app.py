#!/usr/bin/env python3
"""
CDK App for FinAdvisor
Instantiates the main stack
"""

from aws_cdk import core
from cdk_stack import FinAdvisorStack

app = core.App()

FinAdvisorStack(
    app,
    "FinAdvisorStack",
    description="FinAdvisor - AI-Powered Financial Advisory Agent on AWS",
    env=core.Environment(
        account=core.Aws.ACCOUNT_ID,
        region=core.Aws.REGION,
    ),
)

app.synth()
