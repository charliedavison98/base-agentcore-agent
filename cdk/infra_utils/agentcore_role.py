from aws_cdk import (
    aws_iam as iam,
    Stack
)
from constructs import Construct


class AgentCoreRole(iam.Role):
    """IAM role for AgentCore Runtime with necessary permissions"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        region = Stack.of(scope).region
        account_id = Stack.of(scope).account
        
        super().__init__(scope, construct_id,
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("BedrockAgentCoreFullAccess")
            ],
            inline_policies={
                "AgentCorePolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="CloudWatchLogs",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:DescribeLogStreams",
                                "logs:CreateLogGroup",
                                "logs:DescribeLogGroups",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[
                                f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            sid="XRayTracing",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "xray:PutTraceSegments",
                                "xray:PutTelemetryRecords",
                                "xray:GetSamplingRules",
                                "xray:GetSamplingTargets"
                            ],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            sid="CloudWatchMetrics",
                            effect=iam.Effect.ALLOW,
                            actions=["cloudwatch:PutMetricData"],
                            resources=["*"],
                            conditions={
                                "StringEquals": {
                                    "cloudwatch:namespace": "bedrock-agentcore"
                                }
                            }
                        ),
                        iam.PolicyStatement(
                            sid="GetAgentAccessToken",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock-agentcore:GetWorkloadAccessToken",
                                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                                "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
                            ],
                            resources=[
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            sid="BedrockModelInvocation",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:GetInferenceProfile",
                                "bedrock:ListInferenceProfiles",
                                "bedrock:UseInferenceProfile",
                                "bedrock:InvokeModelWithResponseStream"
                            ],
                            resources=[
                                "arn:aws:bedrock:*::foundation-model/*",
                                f"arn:aws:bedrock:{region}:{account_id}:*"
                            ]
                        ),
                        iam.PolicyStatement(
                            sid="AgentCoreMemoryAccess",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock-agentcore:GetMemory",
                                "bedrock-agentcore:ListMemories",
                                "bedrock-agentcore:CreateEvent",
                                "bedrock-agentcore:GetEvent",
                                "bedrock-agentcore:ListEvents",
                                "bedrock-agentcore:DeleteEvent",
                                "bedrock-agentcore:RetrieveMemoryRecords",
                                "bedrock-agentcore:ListMemoryRecords",
                                "bedrock-agentcore:GetMemoryRecord",
                                "bedrock-agentcore:CreateSemanticMemory",
                                "bedrock-agentcore:GetSemanticMemory",
                                "bedrock-agentcore:QuerySemanticMemory"
                            ],
                            resources=[
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            sid="AgentCoreBrowserAccess",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock-agentcore:CreateBrowser",
                                "bedrock-agentcore:ListBrowsers",
                                "bedrock-agentcore:GetBrowser",
                                "bedrock-agentcore:DeleteBrowser",
                                "bedrock-agentcore:StartBrowserSession",
                                "bedrock-agentcore:ListBrowserSessions",
                                "bedrock-agentcore:GetBrowserSession",
                                "bedrock-agentcore:StopBrowserSession",
                                "bedrock-agentcore:UpdateBrowserStream",
                                "bedrock-agentcore:ConnectBrowserAutomationStream",
                                "bedrock-agentcore:ConnectBrowserLiveViewStream"
                            ],
                            resources=[
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:browser/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            sid="S3CodeAccess",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:GetObjectVersion"
                            ],
                            resources=[
                                f"arn:aws:s3:::cdk-*-assets-{account_id}-{region}/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            sid="ECRImageAccess",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ecr:BatchGetImage",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchCheckLayerAvailability"
                            ],
                            resources=[
                                f"arn:aws:ecr:{region}:{account_id}:repository/cdk-*"
                            ]
                        ),
                        iam.PolicyStatement(
                            sid="ECRAuthToken",
                            effect=iam.Effect.ALLOW,
                            actions=["ecr:GetAuthorizationToken"],
                            resources=["*"]
                        )
                    ]
                )
            },
            **kwargs
        )
