"""
AWS CDK Stack for FinAdvisor Application
Deploys all infrastructure including:
- RDS PostgreSQL for LTM (client profiles, recommendations)
- ElastiCache Redis for STM (conversation memory)
- Lambda functions (Orchestrator, MCP servers)
- API Gateway for HTTP endpoints
- AWS App Runner for Streamlit frontend (serverless)
- ECR repositories for Docker images
- VPC with private subnets for database and cache
"""

from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_elasticache as elasticache,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_apprunner as apprunner,
    core,
    Duration,
)
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct


class FinAdvisorStack(core.Stack):
    """Main CDK Stack for FinAdvisor"""

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # VPC
        vpc = ec2.Vpc(
            self,
            "FinAdvisorVpc",
            max_azs=2,
            nat_gateways=1,
            cidr="10.0.0.0/16",
        )

        # RDS PostgreSQL Instance (LTM)
        db_instance = self._create_rds_instance(vpc)

        # ElastiCache Redis Cluster (STM)
        redis_cluster = self._create_redis_cluster(vpc)

        # S3 Bucket for data and logs
        data_bucket = self._create_s3_bucket()

        # Lambda execution role
        lambda_role = self._create_lambda_role(db_instance, data_bucket)

        # Lambda: MCP Postgres Server
        postgres_mcp_lambda = self._create_postgres_mcp_lambda(
            lambda_role, db_instance, vpc
        )

        # Lambda: Market API Server
        market_api_lambda = self._create_market_api_lambda(lambda_role)

        # Lambda: Main Orchestrator
        orchestrator_lambda = self._create_orchestrator_lambda(
            lambda_role, db_instance, redis_cluster, vpc
        )

        # API Gateway
        api = self._create_api_gateway(orchestrator_lambda)

        # ECR Repositories for Docker images
        backend_repo, frontend_repo = self._create_ecr_repositories()

        # App Runner for Streamlit frontend
        app_runner_service = self._create_app_runner_service(
            frontend_repo, api, db_instance, redis_cluster
        )

        # Outputs
        core.CfnOutput(
            self,
            "DbEndpoint",
            value=db_instance.db_instance_endpoint_address,
            description="RDS PostgreSQL Endpoint (LTM)",
        )

        core.CfnOutput(
            self,
            "DbSecretArn",
            value=db_instance.secret.secret_arn if db_instance.secret else "",
            description="Database credentials secret ARN",
        )

        core.CfnOutput(
            self,
            "RedisEndpoint",
            value=redis_cluster.attr_redis_endpoint_address,
            description="ElastiCache Redis Endpoint (STM)",
        )

        core.CfnOutput(
            self,
            "RedisPort",
            value=redis_cluster.attr_redis_endpoint_port,
            description="ElastiCache Redis Port",
        )

        core.CfnOutput(
            self,
            "DataBucketName",
            value=data_bucket.bucket_name,
            description="S3 Data Bucket",
        )

        core.CfnOutput(
            self,
            "ApiEndpoint",
            value=api.url,
            description="API Gateway Endpoint",
        )

        core.CfnOutput(
            self,
            "FrontendUrl",
            value=f"https://{app_runner_service.attr_service_url}",
            description="Streamlit Frontend URL (App Runner)",
        )

        core.CfnOutput(
            self,
            "BackendEcrRepo",
            value=backend_repo.repository_uri,
            description="Backend ECR Repository URI",
        )

        core.CfnOutput(
            self,
            "FrontendEcrRepo",
            value=frontend_repo.repository_uri,
            description="Frontend ECR Repository URI",
        )

    def _create_rds_instance(self, vpc: ec2.Vpc) -> rds.DatabaseInstance:
        """Create RDS PostgreSQL instance"""

        db_security_group = ec2.SecurityGroup(
            self,
            "DbSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for RDS",
        )

        # Allow Lambda to connect to database
        db_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4("10.0.0.0/16"),
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda",
        )

        db_instance = rds.DatabaseInstance(
            self,
            "FinAdvisorDb",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_3
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),
            allocated_storage=20,
            storage_encrypted=True,
            multi_az=False,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_security_group],
            database_name="finadvisor",
            credentials=rds.Credentials.from_username("postgres"),
            backup_retention=core.Duration.days(7),
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        return db_instance

    def _create_redis_cluster(self, vpc: ec2.Vpc) -> elasticache.CfnCacheCluster:
        """Create ElastiCache Redis cluster for STM (Short-Term Memory)"""

        # Create security group for Redis
        redis_security_group = ec2.SecurityGroup(
            self,
            "RedisSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for ElastiCache Redis",
        )

        # Allow Lambda to connect to Redis
        redis_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4("10.0.0.0/16"),
            connection=ec2.Port.tcp(6379),
            description="Allow Lambda to Redis",
        )

        # Create subnet group for Redis
        redis_subnet_group = elasticache.CfnSubnetGroup(
            self,
            "RedisSubnetGroup",
            description="Subnet group for ElastiCache Redis",
            subnet_ids=[subnet.subnet_id for subnet in vpc.private_subnets],
        )

        # Create Redis cluster
        redis_cluster = elasticache.CfnCacheCluster(
            self,
            "FinAdvisorRedis",
            cache_node_type="cache.t3.micro",
            engine="redis",
            num_cache_nodes=1,
            vpc_security_group_ids=[redis_security_group.security_group_id],
            cache_subnet_group_name=redis_subnet_group.ref,
            engine_version="7.0",
            port=6379,
            snapshot_retention_limit=0,  # No snapshots for dev
            auto_minor_version_upgrade=True,
        )

        redis_cluster.add_depends_on(redis_subnet_group)

        return redis_cluster

    def _create_s3_bucket(self) -> s3.Bucket:
        """Create S3 bucket for data and logs"""

        bucket = s3.Bucket(
            self,
            "FinAdvisorData",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        return bucket

    def _create_lambda_role(
        self, db_instance: rds.DatabaseInstance, bucket: s3.Bucket
    ) -> iam.Role:
        """Create IAM role for Lambda functions"""

        role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # RDS access
        db_instance.grant_connect(role, "postgres")

        # S3 access
        bucket.grant_read_write(role)

        # Bedrock access for LLM
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        return role

    def _create_postgres_mcp_lambda(
        self, role: iam.Role, db_instance: rds.DatabaseInstance, vpc: ec2.Vpc
    ) -> lambda_.Function:
        """Create Lambda for PostgreSQL MCP Server"""

        lambda_fn = PythonFunction(
            self,
            "PostgresMcpLambda",
            entry="../backend/mcp_servers",
            handler="postgres_server.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=core.Duration.seconds(60),
            memory_size=512,
            role=role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            environment={
                "DB_HOST": db_instance.db_instance_endpoint_address,
                "DB_NAME": "finadvisor",
                "DB_USER": "postgres",
            },
        )

        return lambda_fn

    def _create_market_api_lambda(self, role: iam.Role) -> lambda_.Function:
        """Create Lambda for Market API MCP Server"""

        lambda_fn = PythonFunction(
            self,
            "MarketApiLambda",
            entry="../backend/mcp_servers",
            handler="market_api_server.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=core.Duration.seconds(30),
            memory_size=256,
            role=role,
        )

        return lambda_fn

    def _create_orchestrator_lambda(
        self,
        role: iam.Role,
        db_instance: rds.DatabaseInstance,
        redis_cluster: elasticache.CfnCacheCluster,
        vpc: ec2.Vpc,
    ) -> lambda_.Function:
        """Create main Orchestrator Lambda"""

        lambda_fn = PythonFunction(
            self,
            "OrchestratorLambda",
            entry="../backend/lambda_orchestrator",
            handler="handler.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=core.Duration.seconds(60),
            memory_size=1024,
            role=role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            environment={
                # PostgreSQL (LTM)
                "DB_HOST": db_instance.db_instance_endpoint_address,
                "DB_PORT": "5432",
                "DB_NAME": "finadvisor",
                "DB_USER": "postgres",
                # Redis (STM)
                "REDIS_HOST": redis_cluster.attr_redis_endpoint_address,
                "REDIS_PORT": redis_cluster.attr_redis_endpoint_port,
                # AWS
                "AWS_REGION": self.region,
                # Model provider (Bedrock)
                "MODEL_PROVIDER": "bedrock",
                "MODEL_NAME": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            },
        )

        return lambda_fn

    def _create_api_gateway(self, orchestrator_lambda: lambda_.Function):
        """Create API Gateway"""

        api = apigateway.RestApi(
            self,
            "FinAdvisorApi",
            rest_api_name="FinAdvisor API",
            description="API for FinAdvisor financial advisor",
            deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
            ),
        )

        # Health check
        health_resource = api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(orchestrator_lambda),
        )

        # Chat endpoint
        chat_resource = api.root.add_resource("chat")
        chat_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(orchestrator_lambda),
        )

        # Recommendation endpoint
        recommendation_resource = api.root.add_resource("recommendation")
        recommendation_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(orchestrator_lambda),
        )

        # Profile endpoint
        profile_resource = api.root.add_resource("profile")
        profile_client_resource = profile_resource.add_resource("{client_id}")
        profile_client_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(orchestrator_lambda),
        )

        # Memory endpoint (debug)
        memory_resource = api.root.add_resource("memory")
        memory_client_resource = memory_resource.add_resource("{client_id}")
        memory_client_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(orchestrator_lambda),
        )

        return api

    def _create_ecr_repositories(self):
        """Create ECR repositories for Docker images"""

        backend_repo = ecr.Repository(
            self,
            "BackendRepository",
            repository_name="finadvisor-backend",
            removal_policy=core.RemovalPolicy.DESTROY,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 5 images",
                    max_image_count=5,
                )
            ],
        )

        frontend_repo = ecr.Repository(
            self,
            "FrontendRepository",
            repository_name="finadvisor-frontend",
            removal_policy=core.RemovalPolicy.DESTROY,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 5 images",
                    max_image_count=5,
                )
            ],
        )

        return backend_repo, frontend_repo

    def _create_app_runner_service(
        self,
        frontend_repo: ecr.Repository,
        api: apigateway.RestApi,
        db_instance: rds.DatabaseInstance,
        redis_cluster: elasticache.CfnCacheCluster,
    ):
        """Create AWS App Runner service for Streamlit frontend"""

        # Create IAM role for App Runner
        app_runner_role = iam.Role(
            self,
            "AppRunnerInstanceRole",
            assumed_by=iam.ServicePrincipal("tasks.apprunner.amazonaws.com"),
        )

        # Grant ECR pull permissions
        frontend_repo.grant_pull(app_runner_role)

        # Create App Runner access role (for ECR)
        app_runner_access_role = iam.Role(
            self,
            "AppRunnerAccessRole",
            assumed_by=iam.ServicePrincipal("build.apprunner.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSAppRunnerServicePolicyForECRAccess"
                ),
            ],
        )

        # App Runner service
        app_runner_service = apprunner.CfnService(
            self,
            "StreamlitAppRunner",
            service_name="finadvisor-frontend",
            source_configuration=apprunner.CfnService.SourceConfigurationProperty(
                authentication_configuration=apprunner.CfnService.AuthenticationConfigurationProperty(
                    access_role_arn=app_runner_access_role.role_arn
                ),
                image_repository=apprunner.CfnService.ImageRepositoryProperty(
                    image_identifier=f"{frontend_repo.repository_uri}:latest",
                    image_repository_type="ECR",
                    image_configuration=apprunner.CfnService.ImageConfigurationProperty(
                        port="8501",
                        runtime_environment_variables=[
                            apprunner.CfnService.KeyValuePairProperty(
                                name="API_ENDPOINT",
                                value=api.url,
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="DB_HOST",
                                value=db_instance.db_instance_endpoint_address,
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="REDIS_HOST",
                                value=redis_cluster.attr_redis_endpoint_address,
                            ),
                        ],
                    ),
                ),
                auto_deployments_enabled=True,
            ),
            instance_configuration=apprunner.CfnService.InstanceConfigurationProperty(
                cpu="1024",  # 1 vCPU
                memory="2048",  # 2 GB
                instance_role_arn=app_runner_role.role_arn,
            ),
            health_check_configuration=apprunner.CfnService.HealthCheckConfigurationProperty(
                protocol="HTTP",
                path="/",
                interval=10,
                timeout=5,
                healthy_threshold=1,
                unhealthy_threshold=5,
            ),
        )

        return app_runner_service
