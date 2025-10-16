"""ECS Fargate service definition."""
from __future__ import annotations

from aws_cdk import Stack, aws_ecs as ecs, aws_ecs_patterns as ecs_patterns
from constructs import Construct


class EcsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "ChopanService",
            cluster=ecs.Cluster(self, "ChopanCluster", vpc=vpc),
            cpu=512,
            desired_count=1,
            memory_limit_mib=1024,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry("public.ecr.aws/docker/library/python:3.12"),
                container_port=8000,
            ),
        )
