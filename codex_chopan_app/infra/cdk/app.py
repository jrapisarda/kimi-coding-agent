"""AWS CDK application entry point."""
import aws_cdk as cdk

from stacks.network_stack import NetworkStack
from stacks.ecs_stack import EcsStack


app = cdk.App()
network = NetworkStack(app, "ChopanNetwork")
EcsStack(app, "ChopanEcs", vpc=network.vpc)
app.synth()
