"""
AWS CDK Stack for FinAdvisor Application
Deploys all infrastructure including:
- RDS PostgreSQL for products and client data
- DynamoDB for memory persistence
- Lambda functions (Orchestrator, MCP servers)
- API Gateway for HTTP endpoints
- VPC with private subnets for database
"""

from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_s3 as s3,
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

        # RDS PostgreSQL Instance
        db_instance = self._create_rds_instance(vpc)

        # DynamoDB Table for Memory
        memory_table = self._create_dynamodb_table()

        # S3 Bucket for data and logs
        data_bucket = self._create_s3_bucket()

        # Lambda execution role
        lambda_role = self._create_lambda_role(db_instance, memory_table, data_bucket)

        # Lambda: MCP Postgres Server
        postgres_mcp_lambda = self._create_postgres_mcp_lambda(
            lambda_role, db_instance, vpc
        )

        # Lambda: Market API Server
        market_api_lambda = self._create_market_api_lambda(lambda_role)

        # Lambda: Main Orchestrator
        orchestrator_lambda = self._create_orchestrator_lambda(
            lambda_role, db_instance, memory_table, vpc
        )

        # API Gateway
        self._create_api_gateway(orchestrator_lambda)

        # Outputs
        core.CfnOutput(
            self,
            "DbEndpoint",
            value=db_instance.db_instance_endpoint_address,
            description="RDS PostgreSQL Endpoint",
        )

        core.CfnOutput(
            self,
            "MemoryTableName",
            value=memory_table.table_name,
            description="DynamoDB Memory Table",
        )

        core.CfnOutput(
            self,
            "DataBucketName",
            value=data_bucket.bucket_name,
            description="S3 Data Bucket",
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

    def _create_dynamodb_table(self) -> dynamodb.Table:
        """Create DynamoDB table for memory persistence"""

        table = dynamodb.Table(
            self,
            "FinAdvisorMemory",
            partition_key=dynamodb.Attribute(
                name="client_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        # Add GSI for queries by timestamp
        table.add_global_secondary_index(
            index_name="TimestampIndex",
            partition_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="client_id", type=dynamodb.AttributeType.STRING
            ),
        )

        return table

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
        self, db_instance: rds.DatabaseInstance, table: dynamodb.Table, bucket: s3.Bucket
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

        # DynamoDB access
        table.grant_read_write_data(role)

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
        memory_table: dynamodb.Table,
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
                "DB_HOST": db_instance.db_instance_endpoint_address,
                "DB_NAME": "finadvisor",
                "DB_USER": "postgres",
                "MEMORY_TABLE": memory_table.table_name,
                "AWS_REGION": self.region,
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

        core.CfnOutput(
            self,
            "ApiEndpoint",
            value=api.url,
            description="API Gateway Endpoint",
        )
