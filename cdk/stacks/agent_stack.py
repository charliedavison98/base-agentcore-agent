from constructs import Construct
from aws_cdk import (
    NestedStack,
    aws_ecr_assets as ecr_assets,
    aws_bedrockagentcore as bedrockagentcore,
    aws_bedrock as bedrock,
    CfnOutput,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_lambda_nodejs as nodejs,
    aws_sns as sns,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    Duration
)
from infra_utils.agentcore_role import AgentCoreRole


class AgentStack(NestedStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage_name: str,
        project_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.stage_name = stage_name

        # Build Docker image locally and push to ECR automatically
        agent_image = ecr_assets.DockerImageAsset(
            self,
            "AgentImage",
            directory="../agent",
            platform=ecr_assets.Platform.LINUX_ARM64,
        )
        
        # Create Bedrock Guardrail for input/output filtering
        guardrail = bedrock.CfnGuardrail(
            self,
            "ChatbotGuardrail",
            name=f"{stage_name}-{project_name}-guardrail",
            description="Blocks jailbreak/harmful content",
            blocked_input_messaging="I can only help with general questions.",
            blocked_outputs_messaging="I'm not able to provide that response.",
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="HATE",
                        input_strength="HIGH",
                        output_strength="HIGH",
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="INSULTS",
                        input_strength="HIGH",
                        output_strength="HIGH",
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="SEXUAL",
                        input_strength="HIGH",
                        output_strength="HIGH",
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="VIOLENCE",
                        input_strength="HIGH",
                        output_strength="HIGH",
                    ),
                ]
            ),
        )

        # Publish a versioned snapshot of the guardrail
        guardrail_version = bedrock.CfnGuardrailVersion(
            self,
            "ChatbotGuardrailVersion",
            guardrail_identifier=guardrail.attr_guardrail_arn,
            description="v1",
        )

        # Create AgentCore execution role
        agent_role = AgentCoreRole(
            self,
            "AgentCoreRole",
            role_name=f"{stage_name}-{project_name}-agentcore-role"
        )
        
        # Grant ECR pull permissions to agent role
        agent_image.repository.grant_pull(agent_role)
        
        # Grant permission to apply the guardrail
        agent_role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=["bedrock:ApplyGuardrail"],
                resources=[guardrail.attr_guardrail_arn]
            )
        )
        
        # Create AgentCore Memory resource
        self.memory_resource = bedrockagentcore.CfnMemory(
            self,
            "ChatbotAgentMemory",
            name=f"{stage_name}_{project_name}_agentcore_memory",
            description=f"Memory resource for chatbot agent in {stage_name} environment",
            event_expiry_duration=90,
            memory_strategies=[
                bedrockagentcore.CfnMemory.MemoryStrategyProperty(
                    user_preference_memory_strategy=bedrockagentcore.CfnMemory.UserPreferenceMemoryStrategyProperty(
                        name="chatbotUserPreferences",
                        namespace_templates=["/chatbot/{actorId}/preferences/"]
                    )
                )
            ]
        )
        
        # Create AgentCore Runtime with container deployment and tracing enabled
        self.agent_runtime = bedrockagentcore.Runtime(
            self,
            "ChatbotAgentRuntime",
            runtime_name=f"{stage_name}_{project_name}_agentcore_runtime",
            agent_runtime_artifact=bedrockagentcore.AgentRuntimeArtifact.from_image_uri(agent_image.image_uri),
            network_configuration=bedrockagentcore.RuntimeNetworkConfiguration.using_public_network(),
            protocol_configuration=bedrockagentcore.ProtocolType.HTTP,
            execution_role=agent_role,
            description=f"Chatbot Agent for {stage_name} environment",
            tracing_enabled=True,
            environment_variables={
                "STAGE": stage_name,
                "AWS_DEFAULT_REGION": self.region,
                "AWS_REGION": self.region,
                "MEMORY_ID": self.memory_resource.attr_memory_id,
                "GUARDRAIL_ID": guardrail.attr_guardrail_id,
                "GUARDRAIL_VERSION": guardrail_version.attr_version,
            }
        )

        lambda_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"{stage_name}-{project_name}-agent-lambda-role",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
            inline_policies={
                "BedrockAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock-agentcore:InvokeAgentRuntime",
                            ],
                            resources=["*"],
                        ),
                    ],
                )
            },
        )

        # Streaming Lambda function for chat (Node.js for native response streaming)
        self.agent_chat_streaming_function = nodejs.NodejsFunction(
            self,
            "AgentChatStreamingFunction",
            entry="lambda_functions/chat_streaming_node/index.mjs",
            deps_lock_file_path="lambda_functions/chat_streaming_node/package-lock.json",
            handler="handler",
            runtime=_lambda.Runtime.NODEJS_20_X,
            function_name=f"{stage_name}-{project_name}-chat-streaming-lambda",
            role=lambda_role,
            environment={
                "AGENT_RUNTIME_ARN": self.agent_runtime.agent_runtime_arn,
            },
            timeout=Duration.seconds(300),
            memory_size=512,
            bundling=nodejs.BundlingOptions(
                external_modules=[],
            ),
        )
  

        # Outputs
        CfnOutput(
            self,
            "AgentRuntimeArn",
            description="ARN of the AgentCore runtime",
            value=self.agent_runtime.agent_runtime_arn
        )

        CfnOutput(
            self,
            "MemoryResourceId",
            description="ID of the AgentCore Memory resource",
            value=self.memory_resource.attr_memory_id
        )

        CfnOutput(
            self,
            "AgentImageUri",
            description="Docker image URI in ECR",
            value=agent_image.image_uri
        )