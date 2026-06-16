from constructs import Construct
from aws_cdk import (
    NestedStack,
    RemovalPolicy,
    CfnOutput,
    Duration,
    aws_cognito as cognito,
    aws_iam as iam,
)


class AuthStack(NestedStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        stage_name: str,
        project_name: str = "chatbot",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.stage_name = stage_name

        # Cognito User Pool for authentication
        self.user_pool = cognito.UserPool(
            self,
            "ChatbotUserPool",
            user_pool_name=f"{stage_name}-{project_name}-user-pool",
            # Allow self-registration
            self_sign_up_enabled=True,
            # Email-only sign-in
            sign_in_aliases=cognito.SignInAliases(email=True, username=False),
            # Password policy
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            # Account recovery
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            # Email verification
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            # Standard attributes
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                given_name=cognito.StandardAttribute(required=False, mutable=True),
                family_name=cognito.StandardAttribute(required=False, mutable=True),
            ),
            # Remove users on stack deletion (dev environment)
            removal_policy=RemovalPolicy.DESTROY,
        )

        # User Pool Client for web application
        self.user_pool_client = cognito.UserPoolClient(
            self,
            "ChatbotUserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name=f"{stage_name}-{project_name}-web-client",
            # OAuth flows
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True,
            ),
            # Token validity
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            # Prevent user existence errors
            prevent_user_existence_errors=True,
            # OAuth settings for future social login
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
                callback_urls=[
                    "http://localhost:3000",
                    "https://localhost:3000",
                ],
                logout_urls=[
                    "http://localhost:3000",
                    "https://localhost:3000",
                ],
            ),
        )

        # Identity Pool for AWS resource access
        self.identity_pool = cognito.CfnIdentityPool(
            self,
            "ChatbotIdentityPool",
            identity_pool_name=f"{stage_name}-{project_name}-identity-pool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=self.user_pool_client.user_pool_client_id,
                    provider_name=self.user_pool.user_pool_provider_name,
                )
            ],
        )

        # IAM roles for authenticated users
        # Authenticated role - minimal permissions
        region_suffix = self.region.replace('-', '')
        self.authenticated_role = iam.Role(
            self,
            "CognitoAuthenticatedRole",
            role_name=f"{stage_name}-{project_name}-cognito-authenticated-role",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
            inline_policies={
                f"CognitoAuthenticatedPolicy-{region_suffix}": iam.PolicyDocument(
                    statements=[
                        # Allow users to get their own identity
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cognito-identity:GetCredentialsForIdentity",
                                "cognito-identity:GetId",
                            ],
                            resources=["*"],
                        ),
                    ]
                )
            },
        )

        # Attach the role to identity pool
        cognito.CfnIdentityPoolRoleAttachment(
            self,
            "IdentityPoolRoleAttachment",
            identity_pool_id=self.identity_pool.ref,
            roles={"authenticated": self.authenticated_role.role_arn},
        )

        # Outputs
        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        CfnOutput(self, "UserPoolArn", value=self.user_pool.user_pool_arn)
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id)
        CfnOutput(self, "IdentityPoolId", value=self.identity_pool.ref)
        CfnOutput(self, "AuthenticatedRoleArn", value=self.authenticated_role.role_arn)
