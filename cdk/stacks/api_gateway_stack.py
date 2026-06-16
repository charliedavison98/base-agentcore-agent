from constructs import Construct
from aws_cdk import (
    NestedStack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_bedrockagentcore as bedrockagentcore,
    CfnOutput,
    Duration
)


class ApiGatewayStack(NestedStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage_name: str,
        user_pool: cognito.UserPool,
        agent_runtime: bedrockagentcore.CfnRuntime,
        agent_chat_streaming_function: _lambda.IFunction,
        project_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.stage_name = stage_name

        # API Gateway with Cognito authorization
        self.api = apigateway.RestApi(
            self,
            "ChatbotApi",
            rest_api_name=f"{stage_name}-{project_name}-serverless-api",
            description="Chatbot Serverless API",
            endpoint_types=[apigateway.EndpointType.REGIONAL],
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "X-Amz-Date",
                    "Authorization",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                ],
            ),
            # Enable API Gateway logging
            cloud_watch_role=True,
            deploy_options=apigateway.StageOptions(
                stage_name=stage_name,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
            ),
        )

        # Cognito authorizer
        cognito_authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_name="CognitoAuthorizer",
        )

        # API routes
        api_resource = self.api.root.add_resource("api")

        # Chat endpoint with streaming enabled
        chat_resource = api_resource.add_resource("chat")
        chat_streaming = chat_resource.add_resource("streaming")
        chat_streaming.add_method(
            "POST",
            apigateway.LambdaIntegration(
                agent_chat_streaming_function,
                response_transfer_mode=apigateway.ResponseTransferMode.STREAM,
                timeout=Duration.seconds(300),
            ),
            authorizer=cognito_authorizer,
        )

        # Outputs
        CfnOutput(self, "ApiGatewayUrl", value=self.api.url)
        CfnOutput(self, "ApiGatewayId", value=self.api.rest_api_id)
        CfnOutput(self, "ApiGatewayRootResourceId", value=self.api.rest_api_root_resource_id)
