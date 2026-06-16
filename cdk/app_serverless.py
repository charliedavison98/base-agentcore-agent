#!/usr/bin/env python3
import warnings
import aws_cdk as cdk
from stacks.main_stack import MainStack

# Suppress typeguard warnings from AWS CDK
warnings.filterwarnings("ignore", message=".*Typeguard cannot check.*")

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region"),
)

stage = app.node.try_get_context("stage")
if not stage:
    raise ValueError("stage context variable is required. Pass --context stage=dev or --context stage=prod")
project_name = app.node.try_get_context("project_name")
stack_name = f"SimpleChatbot-{stage.lower()}"

MainStack(app, stack_name, stage=stage, project_name=project_name, env=env)

app.synth()
