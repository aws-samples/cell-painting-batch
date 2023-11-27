#!/usr/bin/env python3
import aws_cdk as cdk
from stack.network import NetworkStack
from stack.batch import BatchStack
import constants
from cdk_nag import AwsSolutionsChecks, NagSuppressions


app = cdk.App()
#cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

env=constants.DEV_ENV
config=constants.DEV_CONFIG


# Create a network stack
network_stack = NetworkStack(app, "network-cpb", env=env, config=config )

# Create a batch stack
batch_stack = BatchStack(app, "batch-cpb", env=env, config=config, network_stack=network_stack )           


app.synth()
