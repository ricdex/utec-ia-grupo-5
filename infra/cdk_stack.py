"""
AWS CDK Stack for FinAdvisor Application
Deploys all infrastructure including:
- RDS PostgreSQL for LTM (client profiles, recommendations)
- ElastiCache Redis for STM (conversation memory)
- Lambda functions (Orchestrator, MCP servers)
- API Gateway for HTTP endpoints
- EC2 instance for Streamlit frontend
- ECR repositories for Docker images
- VPC with private subnets for database and cache
"""

from __future__ import annotations

import os
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_elasticache as elasticache,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_bedrock as bedrock,
)
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct


class FinAdvisorStack(Stack):
    """Main CDK Stack for FinAdvisor"""

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # VPC
        vpc = ec2.Vpc(
            self,
            "FinAdvisorVpc",
            max_azs=2,
            nat_gateways=1,
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
        )

        # RDS PostgreSQL Instance (LTM)
        db_instance = self._create_rds_instance(vpc)

        # ElastiCache Redis Cluster (STM)
        redis_cluster = self._create_redis_cluster(vpc)

        # S3 Bucket for data and logs
        data_bucket = self._create_s3_bucket()

        # Bedrock Guardrails for financial compliance (optional - may not be available in all CDK versions)
        bedrock_guardrail = None
        try:
            bedrock_guardrail = self._create_bedrock_guardrail()
        except AttributeError:
            print("Warning: Bedrock Guardrails not available in this CDK version. Using local guardrails.")

        # Lambda execution role
        lambda_role = self._create_lambda_role(db_instance, data_bucket, bedrock_guardrail)

        # Lambda: MCP Postgres Server
        postgres_mcp_lambda = self._create_postgres_mcp_lambda(
            lambda_role, db_instance, vpc
        )

        # Lambda: Market API Server
        market_api_lambda = self._create_market_api_lambda(lambda_role)

        # Lambda: Main Orchestrator
        orchestrator_lambda = self._create_orchestrator_lambda(
            lambda_role, db_instance, redis_cluster, vpc, bedrock_guardrail
        )

        # API Gateway
        api = self._create_api_gateway(orchestrator_lambda)

        # ECR Repositories for Docker images
        backend_repo, frontend_repo = self._create_ecr_repositories()

        # EC2 instance for Streamlit frontend
        # Only create if DEPLOY_FRONTEND=true (after images are pushed to ECR)
        deploy_frontend = os.getenv("DEPLOY_FRONTEND", "false").lower() == "true"
        streamlit_instance = None
        streamlit_eip = None

        if deploy_frontend:
            streamlit_instance, streamlit_eip = self._create_ec2_streamlit(
                frontend_repo, api, vpc
            )

        # Outputs
        CfnOutput(
            self,
            "DbEndpoint",
            value=db_instance.db_instance_endpoint_address,
            description="RDS PostgreSQL Endpoint (LTM)",
        )

        CfnOutput(
            self,
            "DbSecretArn",
            value=db_instance.secret.secret_arn if db_instance.secret else "",
            description="Database credentials secret ARN",
        )

        CfnOutput(
            self,
            "RedisEndpoint",
            value=redis_cluster.attr_redis_endpoint_address,
            description="ElastiCache Redis Endpoint (STM)",
        )

        CfnOutput(
            self,
            "RedisPort",
            value=redis_cluster.attr_redis_endpoint_port,
            description="ElastiCache Redis Port",
        )

        CfnOutput(
            self,
            "DataBucketName",
            value=data_bucket.bucket_name,
            description="S3 Data Bucket",
        )

        CfnOutput(
            self,
            "ApiEndpoint",
            value=api.url,
            description="API Gateway Endpoint",
        )

        if streamlit_instance and streamlit_eip:
            CfnOutput(
                self,
                "FrontendUrl",
                value=f"http://{streamlit_eip.ref}:8501",
                description="Streamlit Frontend URL (EC2)",
            )

        CfnOutput(
            self,
            "BackendEcrRepo",
            value=backend_repo.repository_uri,
            description="Backend ECR Repository URI",
        )

        CfnOutput(
            self,
            "FrontendEcrRepo",
            value=frontend_repo.repository_uri,
            description="Frontend ECR Repository URI",
        )

        if bedrock_guardrail:
            CfnOutput(
                self,
                "BedrockGuardrailId",
                value=bedrock_guardrail.attr_guardrail_id,
                description="Bedrock Guardrail ID for financial compliance",
            )

            CfnOutput(
                self,
                "BedrockGuardrailArn",
                value=bedrock_guardrail.attr_guardrail_arn,
                description="Bedrock Guardrail ARN",
            )
        else:
            CfnOutput(
                self,
                "GuardrailsMode",
                value="local",
                description="Guardrails mode (local validation - Bedrock Guardrails not available)",
            )

    def _create_rds_instance(self, vpc: ec2.Vpc) -> rds.DatabaseInstance:
        """
        Create RDS PostgreSQL instance

        NOTA: La base de datos está configurada como públicamente accesible
        para facilitar debugging y verificación de datos. En producción,
        considere cambiar a subnets privadas y publicly_accessible=False.
        """

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

        # Allow public access for debugging and data verification
        db_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(5432),
            description="Allow public access for debugging",
        )

        db_instance = rds.DatabaseInstance(
            self,
            "FinAdvisorDb",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),
            allocated_storage=20,
            storage_encrypted=True,
            multi_az=False,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            publicly_accessible=True,
            security_groups=[db_security_group],
            database_name="finadvisor",
            credentials=rds.Credentials.from_username("postgres"),
            backup_retention=Duration.days(7),
            removal_policy=RemovalPolicy.DESTROY,
        )

        return db_instance

    def _create_redis_cluster(self, vpc: ec2.Vpc) -> elasticache.CfnCacheCluster:
        """
        Create ElastiCache Redis cluster for STM (Short-Term Memory)

        NOTA: El cluster está configurado en subnets públicas con acceso abierto
        para facilitar debugging. En producción, considere usar subnets privadas.
        """

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

        # Allow public access for debugging and data verification
        redis_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(6379),
            description="Allow public access for debugging",
        )

        # Create subnet group for Redis (using public subnets for accessibility)
        redis_subnet_group = elasticache.CfnSubnetGroup(
            self,
            "RedisSubnetGroup",
            description="Subnet group for ElastiCache Redis",
            subnet_ids=[subnet.subnet_id for subnet in vpc.public_subnets],
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
            engine_version="7.1",
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
            removal_policy=RemovalPolicy.DESTROY,
        )

        return bucket

    def _create_lambda_role(
        self, db_instance: rds.DatabaseInstance, bucket: s3.Bucket, guardrail
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

        # AWS Marketplace access for Bedrock model auto-enablement
        # Required for first-time invocation of Anthropic models
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "aws-marketplace:ViewSubscriptions",
                    "aws-marketplace:Subscribe",
                ],
                resources=["*"],
            )
        )

        # Bedrock Guardrails access (if available)
        if guardrail is not None:
            role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "bedrock:ApplyGuardrail",
                    ],
                    resources=[guardrail.attr_guardrail_arn],
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
            index="postgres_server.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(60),
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
            index="market_api_server.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(30),
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
        guardrail,
    ) -> lambda_.Function:
        """Create main Orchestrator Lambda"""

        lambda_fn = PythonFunction(
            self,
            "OrchestratorLambda",
            entry="../backend",  # Include entire backend directory
            index="orchestrator/cloud.py",  # Path to handler file from entry
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(60),
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
                "DB_PASSWORD": db_instance.secret.secret_value_from_json("password").unsafe_unwrap() if db_instance.secret else "postgres",
                # Redis (STM)
                "REDIS_HOST": redis_cluster.attr_redis_endpoint_address,
                "REDIS_PORT": redis_cluster.attr_redis_endpoint_port,
                # Model Configuration (from .env.cloud)
                # Note: AWS_REGION is automatically provided by Lambda runtime
                "MODEL_PROVIDER": os.getenv("MODEL_PROVIDER", "bedrock"),
                "MODEL_NAME": os.getenv("MODEL_NAME", "anthropic.claude-3-sonnet-20240229-v1:0"),
                # API Keys (optional - only if not using Bedrock)
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
                "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
                # Guardrails Configuration
                "GUARDRAILS_PROVIDER": os.getenv("GUARDRAILS_PROVIDER", "bedrock" if guardrail else "local"),
                "AWS_BEDROCK_GUARDRAIL_ID": guardrail.attr_guardrail_id if guardrail else "",
                "AWS_BEDROCK_GUARDRAIL_VERSION": os.getenv("AWS_BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
                # LangSmith Tracing (optional)
                "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2", "false"),
                "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY", ""),
                "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT", "finadvisor-production"),
                "LANGCHAIN_ENDPOINT": os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
                # Judge Evaluation (optional)
                "ENABLE_JUDGE_EVAL": os.getenv("ENABLE_JUDGE_EVAL", "false"),
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
                logging_level=apigateway.MethodLoggingLevel.OFF,
                data_trace_enabled=False,
            ),
            cloud_watch_role=False,
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

        # Models endpoint
        models_resource = api.root.add_resource("models")
        models_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(orchestrator_lambda),
        )

        # Config endpoint
        config_resource = api.root.add_resource("config")
        config_resource.add_method(
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
            removal_policy=RemovalPolicy.RETAIN,  # Keep repository even if stack is deleted
            empty_on_delete=False,  # Don't delete images when repository is removed from stack
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
            removal_policy=RemovalPolicy.RETAIN,  # Keep repository even if stack is deleted
            empty_on_delete=False,  # Don't delete images when repository is removed from stack
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 5 images",
                    max_image_count=5,
                )
            ],
        )

        return backend_repo, frontend_repo

    def _create_ec2_streamlit(
        self,
        frontend_repo: ecr.Repository,
        api: apigateway.RestApi,
        vpc: ec2.Vpc,
    ):
        """Create EC2 instance running Streamlit frontend"""

        # Security group for Streamlit
        streamlit_sg = ec2.SecurityGroup(
            self,
            "StreamlitSecurityGroup",
            vpc=vpc,
            description="Security group for Streamlit frontend",
            allow_all_outbound=True,
        )

        # Allow HTTP traffic on port 8501
        streamlit_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(8501),
            description="Allow Streamlit HTTP traffic",
        )

        # Allow SSH for debugging (optional)
        streamlit_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(22),
            description="Allow SSH",
        )

        # IAM role for EC2
        ec2_role = iam.Role(
            self,
            "StreamlitEC2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
        )

        # Grant ECR pull permissions
        frontend_repo.grant_pull(ec2_role)

        # User data script to install Docker and run Streamlit
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "#!/bin/bash",
            "set -e",
            "# Update system",
            "yum update -y",
            "# Install Docker",
            "amazon-linux-extras install docker -y",
            "systemctl start docker",
            "systemctl enable docker",
            "# Login to ECR",
            f"aws ecr get-login-password --region {self.region} | docker login --username AWS --password-stdin {frontend_repo.repository_uri}",
            "# Pull and run Streamlit container",
            f"docker pull {frontend_repo.repository_uri}:latest",
            f"docker run -d --name streamlit --restart unless-stopped -p 8501:8501 -e API_ENDPOINT={api.url} {frontend_repo.repository_uri}:latest",
        )

        # Create EC2 instance
        instance = ec2.Instance(
            self,
            "StreamlitInstance",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.SMALL,  # t3.small - 2GB RAM
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=streamlit_sg,
            role=ec2_role,
            user_data=user_data,
        )

        # Elastic IP for stable public IP
        eip = ec2.CfnEIP(
            self,
            "StreamlitEIP",
            instance_id=instance.instance_id,
        )

        return instance, eip

    def _create_bedrock_guardrail(self) -> bedrock.CfnGuardrail:
        """Create Bedrock Guardrail for financial compliance"""

        guardrail = bedrock.CfnGuardrail(
            self,
            "FinancialGuardrailV6",
            name="finadvisor-financial-compliance-v6",
            description="Guardrails for financial advisory compliance and safety",
            blocked_input_messaging="Lo siento, no puedo procesar esa solicitud por cumplimiento normativo financiero.",
            blocked_outputs_messaging="Lo siento, no puedo proporcionar esa información por restricciones de cumplimiento.",

            # Content Policy Configuration
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    # Hate and Abusive Language
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="HATE",
                        input_strength="HIGH",
                        output_strength="HIGH"
                    ),
                    # Insults
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="INSULTS",
                        input_strength="MEDIUM",
                        output_strength="MEDIUM"
                    ),
                    # Sexual Content
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="SEXUAL",
                        input_strength="HIGH",
                        output_strength="HIGH"
                    ),
                    # Violence
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="VIOLENCE",
                        input_strength="MEDIUM",
                        output_strength="MEDIUM"
                    ),
                    # Misconduct (new in Bedrock)
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="MISCONDUCT",
                        input_strength="HIGH",
                        output_strength="HIGH"
                    ),
                ]
            ),

            # Topic Policy Configuration - Financial specific
            topic_policy_config=bedrock.CfnGuardrail.TopicPolicyConfigProperty(
                topics_config=[
                    # Prohibited: Guaranteed returns
                    bedrock.CfnGuardrail.TopicConfigProperty(
                        name="RetornosGarantizados",
                        definition="Discusiones sobre retornos de inversión garantizados, ganancias aseguradas, o promesas de rendimiento sin riesgo.",
                        examples=[
                            "Te garantizo que obtendrás 20% de retorno",
                            "Esta inversión es completamente segura y sin riesgo",
                            "Ganancias garantizadas del 100%"
                        ],
                        type="DENY"
                    ),
                    # Prohibited: Unauthorized investments
                    bedrock.CfnGuardrail.TopicConfigProperty(
                        name="InversionesNoAutorizadas",
                        definition="Recomendaciones sobre criptomonedas, forex no regulado, esquemas piramidales, o inversiones no autorizadas por la regulación.",
                        examples=[
                            "Deberías invertir en Bitcoin",
                            "Te recomiendo este esquema multinivel",
                            "Compra esta criptomoneda antes de que suba"
                        ],
                        type="DENY"
                    ),
                    # Prohibited: Market timing
                    bedrock.CfnGuardrail.TopicConfigProperty(
                        name="PredictionsEspeculativas",
                        definition="Predicciones específicas sobre movimientos del mercado o timing del mercado.",
                        examples=[
                            "El mercado va a colapsar mañana",
                            "Vende todo ahora, el crash viene",
                            "Este producto subirá 50% el próximo mes"
                        ],
                        type="DENY"
                    ),
                    # Prohibited: Tax evasion
                    bedrock.CfnGuardrail.TopicConfigProperty(
                        name="EvasionFiscal",
                        definition="Consejos sobre evasión fiscal, ocultamiento de activos, o fraude tributario.",
                        examples=[
                            "Así puedes esconder dinero del SAT",
                            "No declares estos ingresos",
                            "Usa esta cuenta offshore para evadir impuestos"
                        ],
                        type="DENY"
                    ),
                    # Prohibited: Insider trading
                    bedrock.CfnGuardrail.TopicConfigProperty(
                        name="InformacionPrivilegiada",
                        definition="Uso o recomendación de información privilegiada para trading.",
                        examples=[
                            "Tengo información interna sobre esta empresa",
                            "Un ejecutivo me dijo que van a anunciar fusión",
                            "Compra antes de que salga la noticia"
                        ],
                        type="DENY"
                    ),
                ]
            ),

            # Word Policy Configuration - Financial prohibited terms
            word_policy_config=bedrock.CfnGuardrail.WordPolicyConfigProperty(
                words_config=[
                    bedrock.CfnGuardrail.WordConfigProperty(text="garantizado"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="garantizada"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="sin riesgo"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="100% seguro"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="ganancias aseguradas"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="retorno garantizado"),
                ],
                managed_word_lists_config=[
                    # Use AWS managed profanity filter
                    bedrock.CfnGuardrail.ManagedWordsConfigProperty(
                        type="PROFANITY"
                    )
                ]
            ),

            # Sensitive Information Policy - PII protection
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    # Email
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="EMAIL",
                        action="ANONYMIZE"
                    ),
                    # Phone
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="PHONE",
                        action="ANONYMIZE"
                    ),
                    # Credit/Debit Card
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="CREDIT_DEBIT_CARD_NUMBER",
                        action="BLOCK"
                    ),
                    # SSN/Tax ID
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="US_SOCIAL_SECURITY_NUMBER",
                        action="BLOCK"
                    ),
                    # Address
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="ADDRESS",
                        action="ANONYMIZE"
                    ),
                    # Name
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="NAME",
                        action="ANONYMIZE"
                    ),
                ]
            ),
        )

        return guardrail
