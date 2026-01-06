#!/bin/bash
#
# FinAdvisor Cloud Deployment Script
# Deploys complete infrastructure to AWS with seed data
#
# Usage: ./scripts/deploy_cloud.sh [--stack-name STACK_NAME] [--region REGION]
#

set -e  # Exit on error

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
STACK_NAME="${STACK_NAME:-FinAdvisorStack}"
AWS_REGION="${AWS_REGION:-us-east-1}"
PROFILE="${AWS_PROFILE:-default}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --stack-name NAME    CloudFormation stack name (default: FinAdvisorStack)"
            echo "  --region REGION      AWS region (default: us-east-1)"
            echo "  --profile PROFILE    AWS profile (default: default)"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     FinAdvisor - AWS Cloud Deployment Script              ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  Stack Name: $STACK_NAME"
echo "  Region: $AWS_REGION"
echo "  Profile: $PROFILE"
echo ""

# ============================================================
# STEP 1: Validate Prerequisites
# ============================================================

echo -e "${CYAN}[1/6] Validating prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not found${NC}"
    echo "Install: https://aws.amazon.com/cli/"
    exit 1
fi
echo -e "${GREEN}✓ AWS CLI installed${NC}"

# Check CDK
if ! command -v cdk &> /dev/null; then
    echo -e "${RED}✗ AWS CDK not found${NC}"
    echo "Install: npm install -g aws-cdk"
    exit 1
fi
echo -e "${GREEN}✓ AWS CDK installed${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 installed${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    echo "Install: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# .env file not required for cloud - all config comes from CDK
if [ -f .env ]; then
    echo -e "${GREEN}✓ .env file found (will be used for local testing)${NC}"
else
    echo -e "${YELLOW}⚠ .env file not found (not required for cloud deployment)${NC}"
fi

# Validate AWS credentials
if ! aws sts get-caller-identity --profile "$PROFILE" --region "$AWS_REGION" &> /dev/null; then
    echo -e "${RED}✗ AWS credentials invalid${NC}"
    echo "Configure: aws configure --profile $PROFILE"
    exit 1
fi
ACCOUNT_ID=$(aws sts get-caller-identity --profile "$PROFILE" --region "$AWS_REGION" --query Account --output text)
echo -e "${GREEN}✓ AWS credentials valid (Account: $ACCOUNT_ID)${NC}"

# Check Bedrock access (REQUIRED)
echo -e "${CYAN}Checking Bedrock access...${NC}"
if aws bedrock list-foundation-models --region "$AWS_REGION" --profile "$PROFILE" --by-provider anthropic &> /dev/null 2>&1; then
    # Check if Claude models are specifically available
    CLAUDE_AVAILABLE=$(aws bedrock list-foundation-models \
        --region "$AWS_REGION" \
        --profile "$PROFILE" \
        --by-provider anthropic \
        --query 'modelSummaries[?contains(modelId, `claude-3-5`)].modelId' \
        --output text 2>/dev/null | wc -l | tr -d ' ')

    if [ "$CLAUDE_AVAILABLE" -gt 0 ]; then
        echo -e "${GREEN}✓ Bedrock access enabled (Claude 3.5 available)${NC}"
    else
        echo -e "${RED}✗ Bedrock access enabled but Claude models not available${NC}"
        echo -e "${YELLOW}Action required:${NC}"
        echo "  1. Go to: https://console.aws.amazon.com/bedrock/home#/modelaccess"
        echo "  2. Click 'Manage model access'"
        echo "  3. Enable: Anthropic Claude 3.5 Sonnet v2"
        echo "  4. Click 'Save changes'"
        echo "  5. Wait 1-2 minutes for activation"
        echo "  6. Re-run: make deploy-aws"
        exit 1
    fi
else
    echo -e "${RED}✗ Bedrock access not enabled${NC}"
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  REQUIRED: Enable Bedrock Model Access (2 minutes)${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  1. Open: https://console.aws.amazon.com/bedrock/home#/modelaccess"
    echo "  2. Select region: $AWS_REGION"
    echo "  3. Click 'Manage model access'"
    echo "  4. Enable: ✓ Anthropic Claude 3.5 Sonnet v2"
    echo "  5. Click 'Save changes'"
    echo "  6. Wait until status shows 'Access granted' (~1-2 min)"
    echo "  7. Come back and re-run: make deploy-aws"
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
    exit 1
fi

echo ""

# ============================================================
# STEP 2: Build Docker Images
# ============================================================

echo -e "${CYAN}[2/6] Building Docker images...${NC}"

# Build backend image
echo "Building backend image..."
docker build -t finadvisor-backend:latest -f backend/Dockerfile . || {
    echo -e "${RED}✗ Backend build failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ Backend image built${NC}"

# Build frontend image
echo "Building frontend image..."
docker build -t finadvisor-frontend:latest -f frontend/Dockerfile . || {
    echo -e "${RED}✗ Frontend build failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ Frontend image built${NC}"

echo ""

# ============================================================
# STEP 3: Deploy CDK Stack
# ============================================================

echo -e "${CYAN}[3/6] Deploying infrastructure with CDK...${NC}"

cd infra

# Install CDK dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing CDK dependencies..."
    npm install
fi

# Bootstrap CDK (if not already done)
echo "Bootstrapping CDK..."
cdk bootstrap aws://$ACCOUNT_ID/$AWS_REGION --profile "$PROFILE" || true

# Deploy stack
echo "Deploying stack: $STACK_NAME..."
cdk deploy "$STACK_NAME" \
    --profile "$PROFILE" \
    --region "$AWS_REGION" \
    --require-approval never \
    --outputs-file ../cdk-outputs.json || {
    echo -e "${RED}✗ CDK deployment failed${NC}"
    exit 1
}

cd ..

echo -e "${GREEN}✓ Infrastructure deployed${NC}"
echo ""

# ============================================================
# STEP 4: Extract Outputs
# ============================================================

echo -e "${CYAN}[4/7] Extracting deployment outputs...${NC}"

if [ ! -f "cdk-outputs.json" ]; then
    echo -e "${RED}✗ CDK outputs file not found${NC}"
    exit 1
fi

# Parse outputs
DB_ENDPOINT=$(jq -r ".[\"$STACK_NAME\"].DbEndpoint" cdk-outputs.json)
REDIS_ENDPOINT=$(jq -r ".[\"$STACK_NAME\"].RedisEndpoint" cdk-outputs.json)
REDIS_PORT=$(jq -r ".[\"$STACK_NAME\"].RedisPort" cdk-outputs.json)
API_ENDPOINT=$(jq -r ".[\"$STACK_NAME\"].ApiEndpoint" cdk-outputs.json)
FRONTEND_URL=$(jq -r ".[\"$STACK_NAME\"].FrontendUrl // empty" cdk-outputs.json)
BACKEND_ECR=$(jq -r ".[\"$STACK_NAME\"].BackendEcrRepo" cdk-outputs.json)
FRONTEND_ECR=$(jq -r ".[\"$STACK_NAME\"].FrontendEcrRepo" cdk-outputs.json)

echo "DB Endpoint: $DB_ENDPOINT"
echo "Redis Endpoint: $REDIS_ENDPOINT:$REDIS_PORT"
echo "API Endpoint: $API_ENDPOINT"
echo "Backend ECR: $BACKEND_ECR"
echo "Frontend ECR: $FRONTEND_ECR"

if [ -n "$FRONTEND_URL" ]; then
    echo "Frontend URL: $FRONTEND_URL"
fi

echo -e "${GREEN}✓ Outputs extracted${NC}"
echo ""

# ============================================================
# STEP 5: Push Images to ECR
# ============================================================

echo -e "${CYAN}[5/7] Pushing Docker images to ECR...${NC}"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" --profile "$PROFILE" | \
    docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com" || {
    echo -e "${RED}✗ ECR login failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ ECR login successful${NC}"

# Tag and push backend image
echo "Pushing backend image..."
docker tag finadvisor-backend:latest "$BACKEND_ECR:latest"
docker push "$BACKEND_ECR:latest" || {
    echo -e "${RED}✗ Backend image push failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ Backend image pushed${NC}"

# Tag and push frontend image
echo "Pushing frontend image..."
docker tag finadvisor-frontend:latest "$FRONTEND_ECR:latest"
docker push "$FRONTEND_ECR:latest" || {
    echo -e "${RED}✗ Frontend image push failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ Frontend image pushed${NC}"

# Trigger App Runner deployment
echo "Waiting for App Runner to deploy new frontend image..."
sleep 10
echo -e "${GREEN}✓ Images deployed to ECR${NC}"
echo ""

# ============================================================
# STEP 6: Seed Database
# ============================================================

echo -e "${CYAN}[6/7] Seeding database with initial data...${NC}"

# Get DB password from Secrets Manager
DB_SECRET_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --profile "$PROFILE" \
    --query "Stacks[0].Outputs[?OutputKey=='DbSecretArn'].OutputValue" \
    --output text 2>/dev/null || echo "")

if [ -n "$DB_SECRET_ARN" ]; then
    echo "Retrieving database password from Secrets Manager..."
    DB_PASSWORD=$(aws secretsmanager get-secret-value \
        --secret-id "$DB_SECRET_ARN" \
        --region "$AWS_REGION" \
        --profile "$PROFILE" \
        --query SecretString \
        --output text | jq -r .password)
else
    echo -e "${YELLOW}⚠ DB secret not found. Using default password.${NC}"
    DB_PASSWORD="postgres"
fi

# Wait for database to be ready
echo "Waiting for database to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U postgres -d finadvisor -c "SELECT 1" &> /dev/null; then
        echo -e "${GREEN}✓ Database is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for database... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 10
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Database not ready after $MAX_RETRIES attempts${NC}"
    echo -e "${YELLOW}⚠ You may need to run seed manually:${NC}"
    echo "DB_HOST=$DB_ENDPOINT DB_PASSWORD=$DB_PASSWORD python3 scripts/seed_database.py"
    exit 1
fi

# Run seed script
echo "Loading data from CSV files..."
DB_HOST="$DB_ENDPOINT" \
DB_PORT="5432" \
DB_NAME="finadvisor" \
DB_USER="postgres" \
DB_PASSWORD="$DB_PASSWORD" \
python3 scripts/seed_database.py || {
    echo -e "${RED}✗ Database seeding failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ Database seeded successfully${NC}"
echo ""

# ============================================================
# STEP 7: Display Results
# ============================================================

echo -e "${CYAN}[7/7] Deployment complete!${NC}"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              🎉 Deployment Successful!                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📋 Deployment Information:${NC}"
echo ""
echo "  Stack Name: $STACK_NAME"
echo "  Region: $AWS_REGION"
echo "  Account: $ACCOUNT_ID"
echo ""
echo -e "${CYAN}🌐 Service Endpoints:${NC}"
echo ""

if [ -n "$FRONTEND_URL" ]; then
    echo -e "  ${GREEN}Frontend (Streamlit):${NC}"
    echo "    $FRONTEND_URL"
    echo ""
fi

echo -e "  ${GREEN}Backend API:${NC}"
echo "    $API_ENDPOINT"
echo ""
echo -e "  ${GREEN}API Documentation:${NC}"
echo "    ${API_ENDPOINT}docs"
echo ""

echo -e "${CYAN}🗄️ Database:${NC}"
echo ""
echo "  PostgreSQL: $DB_ENDPOINT:5432"
echo "  Database: finadvisor"
echo "  User: postgres"
echo ""
echo "  Redis: $REDIS_ENDPOINT:$REDIS_PORT"
echo ""

echo -e "${CYAN}📊 Seed Data Loaded:${NC}"
echo ""
echo "  ✓ Products (from data/products.csv)"
echo "  ✓ Clients (from data/clients.csv)"
echo "  ✓ Portfolios (from data/portfolios.csv)"
echo ""

echo -e "${CYAN}🚀 Next Steps:${NC}"
echo ""

if [ -n "$FRONTEND_URL" ]; then
    echo "  1. Open the Streamlit frontend:"
    echo "     $FRONTEND_URL"
    echo ""
    echo "  2. Select a client (CLI001, CLI002, CLI003, CLI004)"
    echo ""
    echo "  3. Click 'Cargar Perfil'"
    echo ""
    echo "  4. Start chatting: 'que productos me puedes recomendar'"
else
    echo "  1. Access the API at:"
    echo "     $API_ENDPOINT"
    echo ""
    echo "  2. Test with curl:"
    echo "     curl $API_ENDPOINT/health"
    echo ""
    echo "  3. For Streamlit, run locally and point to API:"
    echo "     API_ENDPOINT=$API_ENDPOINT streamlit run frontend/app.py"
fi

echo ""
echo -e "${CYAN}🔧 Useful Commands:${NC}"
echo ""
echo "  View logs:"
echo "    aws logs tail /aws/lambda/${STACK_NAME}-OrchestratorLambda --follow --profile $PROFILE --region $AWS_REGION"
echo ""
echo "  Connect to database:"
echo "    PGPASSWORD='$DB_PASSWORD' psql -h $DB_ENDPOINT -U postgres -d finadvisor"
echo ""
echo "  Update stack:"
echo "    ./scripts/deploy_cloud.sh"
echo ""
echo "  Destroy stack:"
echo "    cd infra && cdk destroy $STACK_NAME --profile $PROFILE --region $AWS_REGION"
echo ""

# Save outputs to file
cat > deployment-info.txt <<EOF
FinAdvisor AWS Deployment
========================

Deployment Date: $(date)
Stack Name: $STACK_NAME
Region: $AWS_REGION
Account: $ACCOUNT_ID

Service Endpoints
-----------------
Frontend: $FRONTEND_URL
Backend API: $API_ENDPOINT
API Docs: ${API_ENDPOINT}docs

Database
--------
PostgreSQL: $DB_ENDPOINT:5432
Database: finadvisor
User: postgres
Password: [See Secrets Manager: $DB_SECRET_ARN]

Redis: $REDIS_ENDPOINT:$REDIS_PORT

Seed Data
---------
✓ Products loaded from data/products.csv
✓ Clients loaded from data/clients.csv
✓ Portfolios loaded from data/portfolios.csv
EOF

echo -e "${GREEN}✓ Deployment info saved to: deployment-info.txt${NC}"
echo ""
echo -e "${GREEN}Deployment complete! 🎉${NC}"
