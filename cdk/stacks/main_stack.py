from constructs import Construct
from aws_cdk import Stack, CfnOutput

from .auth_stack import AuthStack
from .api_gateway_stack import ApiGatewayStack
from .agent_stack import AgentStack
from .frontend_stack import FrontendStack


class MainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, stage: str, project_name: str, **kwargs) -> None:
        kwargs["cross_region_references"] = True
        super().__init__(scope, construct_id, **kwargs)

        stage_name = (stage or "dev").lower()

        self.stage = stage_name

        # Authentication resources
        self.auth_stack = AuthStack(
            self,
            "AuthStack",
            stage_name=stage_name,
            project_name=project_name,
        )

        # AgentCore resources
        self.agent_stack = AgentStack(
            self,
            "AgentStack",
            stage_name=stage_name,
            project_name=project_name,
        )

        # API resources
        self.api = ApiGatewayStack(
            self,
            "Api",
            user_pool=self.auth_stack.user_pool,
            stage_name=stage_name,
            project_name=project_name,
            agent_runtime=self.agent_stack.agent_runtime,
            agent_chat_streaming_function=self.agent_stack.agent_chat_streaming_function,
        )

        # Frontend hosting — after ApiGatewayStack so we can wire the /api/* proxy behavior
        self.frontend_stack = FrontendStack(
            self,
            "FrontendStack",
            stage_name=stage_name,
            project_name=project_name,
            api_gateway=self.api.api,
        )

        # Surface key outputs at the main stack level
        CfnOutput(self, "WebsiteUrl", value=self.frontend_stack.website_url)
        CfnOutput(self, "ApiGatewayUrl", value=self.api.api.url)
        CfnOutput(self, "UserPoolId", value=self.auth_stack.user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=self.auth_stack.user_pool_client.user_pool_client_id)
        CfnOutput(self, "FrontendBucketName", value=self.frontend_stack.bucket.bucket_name)
        CfnOutput(self, "CloudFrontDistributionId", value=self.frontend_stack.distribution.distribution_id)
