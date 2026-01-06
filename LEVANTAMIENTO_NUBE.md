# ☁️ Levantamiento en AWS

Desplegar FinAdvisor en AWS con Bedrock (Claude 3.5 Sonnet).

---

## ✅ Pre-requisitos

```bash
# AWS CLI configurado
aws configure

# Node.js 18+
node --version

# CDK instalado
npm install -g aws-cdk

# Python 3.11+
python3 --version

# Verificar credenciales
aws sts get-caller-identity
```

---

## 🚀 Deployment

### 1. Preparar Infraestructura
```bash
cd infra
pip install -r requirements.txt
cdk bootstrap  # Solo primera vez
cdk diff       # Ver cambios
```

### 2. Desplegar Stack
```bash
cdk deploy
# Esperar ~15 minutos
```

**Outputs importantes:**
```
FinAdvisorStack.DbEndpoint = finadvisor-db.xxxxx.rds.amazonaws.com
FinAdvisorStack.RedisEndpoint = finadvisor-redis.xxxxx.cache.amazonaws.com
FinAdvisorStack.RedisPort = 6379
FinAdvisorStack.ApiEndpoint = https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/
```

### 3. Inicializar Base de Datos

Conéctate a un EC2 o usa AWS Cloud9 en la misma VPC:

```bash
# Conectar a PostgreSQL
export DB_ENDPOINT=<DbEndpoint del output>
psql -h $DB_ENDPOINT -U postgres -d finadvisor -f ../data/init_db.sql

# Cargar datos de productos
cd ..
python3 scripts/seed_database.py
python3 scripts/seed_rag.py
```

### 4. Verificar Deployment
```bash
export API_ENDPOINT=<ApiEndpoint del output>
curl $API_ENDPOINT/health
```

---

## 🔧 Configuración Bedrock

En `backend/utils/config.py`, el modelo se auto-selecciona:

```json
{
  "model": {
    "provider": "bedrock",
    "name": "anthropic.claude-3-5-sonnet-20241022-v2:0"
  }
}
```

O configurable via `.env`:
```
MODEL_PROVIDER=bedrock
MODEL_NAME=anthropic.claude-3-5-sonnet-20241022-v2:0
AWS_REGION=us-east-1
```

---

## ✅ Verificación y Testing

### Health Check
```bash
curl $API_ENDPOINT/health
```

### Probar Chat
```bash
curl -X POST $API_ENDPOINT/chat \
  -H "Content-Type: application/json" \
  -d '{"client_id":"CLI001","message":"Hola"}'
```

### Generar Recomendación
```bash
curl -X POST $API_ENDPOINT/recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "client_id":"CLI001",
    "amount":50000,
    "risk_profile":"moderado",
    "months":24,
    "target_return":8.0
  }'
```

### Verificar Memorias

#### STM (Redis - Conversaciones)
```bash
# Conectar a Redis desde EC2 en la misma VPC
redis-cli -h <RedisEndpoint> -p 6379

# Ver conversaciones
> KEYS conversation:*
> LRANGE conversation:CLI001 0 -1
> TTL conversation:CLI001
```

#### LTM (PostgreSQL - Datos)
```bash
# Conectar a PostgreSQL
psql -h <DbEndpoint> -U postgres -d finadvisor

# Verificar datos
SELECT COUNT(*) FROM products;      -- Debe ser 8
SELECT COUNT(*) FROM clients;       -- Debe ser >= 1
SELECT * FROM portfolio_recommendations ORDER BY recommendation_date DESC;
```

---

## 📊 Monitoreo

### Logs de Lambda
```bash
# Ver logs en tiempo real
aws logs tail /aws/lambda/FinAdvisorStack-OrchestratorLambda --follow

# Ver últimos errores
aws logs filter-pattern /aws/lambda/FinAdvisorStack-OrchestratorLambda \
  --filter-pattern "ERROR"
```

### Estado de Servicios
```bash
# RDS PostgreSQL
aws rds describe-db-instances \
  --db-instance-identifier finadvisor-db \
  --query 'DBInstances[0].DBInstanceStatus'

# ElastiCache Redis
aws elasticache describe-cache-clusters \
  --cache-cluster-id finadvisor-redis \
  --query 'CacheClusters[0].CacheClusterStatus'
```

### Métricas CloudWatch
```bash
# Invocaciones de Lambda
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=FinAdvisorStack-OrchestratorLambda \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Errores de Lambda
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=FinAdvisorStack-OrchestratorLambda \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

---

## 💰 Costos (~$30/mes)

| Servicio | Costo Mensual |
|----------|---------------|
| **RDS PostgreSQL** (t3.micro) | ~$15.00 |
| **ElastiCache Redis** (t3.micro) | ~$12.00 |
| **Lambda** (pay-per-use) | ~$0.20-5.00 |
| **API Gateway** | ~$3.50 |
| **S3 Data Bucket** | ~$0.50 |
| **Data Transfer** | ~$0.30 |
| **TOTAL ESTIMADO** | **~$31-36/mes** |

**Nota:** Redis y PostgreSQL son los principales costos (managed services). Lambda y API Gateway son pay-per-use.

---

## 🧹 Cleanup

```bash
cd infra
cdk destroy --force
```

---

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| Deploy falla | Revisar permisos IAM |
| RDS error | Verificar security group |
| Bedrock error | Verificar región tiene Bedrock |
| Timeout Lambda | `aws lambda update-function-configuration --function-name FinAdvisorStack-OrchestratorLambda --timeout 60` |

---

**Ver arquitectura:** [README.md](./README.md)
