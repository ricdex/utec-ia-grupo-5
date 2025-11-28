# ☁️ Levantamiento en AWS

Desplegar FinAdvisor en AWS con Bedrock (Claude 3.5 Sonnet equivalente).

---

## 📋 Prerequisites

```bash
# AWS CLI configurado
aws configure

# Node.js 18+
node --version

# CDK instalado
npm install -g aws-cdk

# Verificar credenciales
aws sts get-caller-identity
```

---

## 🚀 Deployment (5 pasos)

### 1. Preparar Infraestructura
```bash
cd infra
pip install -r requirements.txt
cdk synth
cdk diff
```

### 2. Desplegar
```bash
cdk deploy --require-approval never
# Esperar ~15 minutos
```

**Guardar outputs:**
- API Endpoint
- DB Host
- Lambda Role ARN

### 3. Inicializar BD
```bash
export DB_ENDPOINT=finadvisor-db.xxxxx.rds.amazonaws.com
export DB_USER=postgres
export DB_PASSWORD=<password>

psql -h $DB_ENDPOINT -U $DB_USER -d finadvisor \
  -f ../data/init_db.sql
```

### 4. Cargar Datos
```bash
cd ..
python3 scripts/seed_rag.py
```

### 5. Verificar
```bash
export API_ENDPOINT=$(cd infra && cdk output ApiEndpoint)
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

## ✅ Verificación

```bash
# Health check
curl $API_ENDPOINT/health

# Chat
curl -X POST $API_ENDPOINT/chat \
  -H "Content-Type: application/json" \
  -d '{"client_id":"CLI001","message":"Hola"}'

# Recomendación
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

---

## 📊 Monitoreo

```bash
# Ver logs Lambda
aws logs tail /aws/lambda/FinAdvisorStack-OrchestratorLambda --follow

# Verificar RDS
aws rds describe-db-instances \
  --db-instance-identifier finadvisor-db \
  --query 'DBInstances[0].DBInstanceStatus'

# Ver métricas
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=FinAdvisorStack-OrchestratorLambda \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

---

## 💰 Costos (~$12/mes)

| Servicio | Costo |
|----------|-------|
| Lambda | $0.20 |
| RDS t3.micro | $7.00 |
| DynamoDB | $1.00 |
| API Gateway | $3.50 |
| Data Transfer | $0.30 |

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
