# ☁️ Guía de Despliegue en AWS

Guía completa para desplegar FinAdvisor en AWS con automatización total de infraestructura.

---

## 🎯 Resumen

Este despliegue crea una infraestructura **completamente serverless y lista para producción** en AWS:

- **Backend**: Funciones Lambda + API Gateway
- **Frontend**: Streamlit en AWS App Runner (contenedores serverless)
- **Base de Datos**: RDS PostgreSQL (LTM - Memoria de Largo Plazo)
- **Caché**: ElastiCache Redis (STM - Memoria de Corto Plazo)
- **LLM**: AWS Bedrock (Claude 3.5 Sonnet/Haiku)
- **Registro de Contenedores**: ECR (Elastic Container Registry)
- **Infraestructura como Código**: AWS CDK (Cloud Development Kit)

**Estimación de costos**: ~$50-100/mes con uso moderado (escala a casi $0 cuando no se usa)

---

## 📋 Prerrequisitos

### 1. Configuración de Cuenta AWS

- Cuenta AWS con acceso administrativo
- AWS CLI instalado y configurado
- **Acceso a Bedrock habilitado** para modelos Claude (región us-east-1 recomendada)

```bash
# Instalar AWS CLI
brew install awscli  # macOS
# o: https://aws.amazon.com/cli/

# Configurar credenciales
aws configure
# AWS Access Key ID: [tu-key]
# AWS Secret Access Key: [tu-secret]
# Default region: us-east-1
# Default output format: json

# Verificar
aws sts get-caller-identity
```

### 2. Habilitar AWS Bedrock (Paso Manual)

⚠️ **PASO MANUAL REQUERIDO**: Debes habilitar el acceso a modelos de Bedrock antes del despliegue.

**¿Por qué es manual?** AWS requiere aprobación manual para acceso a modelos de IA (seguridad/cumplimiento).

**Pasos (toma 2-5 minutos):**

1. **Abrir Consola de Bedrock**:
   ```
   https://console.aws.amazon.com/bedrock/home#/modelaccess
   ```

2. **Seleccionar Región**: Elegir **us-east-1** (recomendada para mejor disponibilidad)

3. **Clic en "Manage model access"**

4. **Habilitar modelos Claude**:
   - ✅ `Anthropic Claude 3.5 Sonnet v2` (recomendado para producción)
   - ✅ `Anthropic Claude 3.5 Haiku v2` (alternativa económica)

5. **Clic en "Save changes"**

6. **Esperar activación**: El estado cambia de "Available to request" → **"Access granted"** (~1-2 minutos)

7. **Verificar**: Ejecuta este comando
   ```bash
   aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic
   ```

   Debería mostrar modelos con `modelId` como `anthropic.claude-3-5-sonnet-20241022-v2:0`

**✅ ¡Listo!** Continúa al siguiente paso.

### 3. Instalar Herramientas

```bash
# AWS CDK
npm install -g aws-cdk

# Verificar
cdk --version  # Debe ser >= 2.0.0

# Docker (requerido para construir imágenes)
docker --version

# jq (para parsear JSON)
brew install jq  # macOS
# o: apt-get install jq  # Linux
```

### 4. Configurar Entorno (Opcional)

**Buenas noticias:** ¡El archivo `.env` **NO es requerido** para despliegue en la nube!

Toda la configuración se maneja automáticamente por CDK:
- ✅ `DB_HOST`, `DB_PASSWORD` → CDK crea RDS y guarda la contraseña en Secrets Manager
- ✅ `REDIS_HOST` → CDK crea ElastiCache
- ✅ `MODEL_PROVIDER` → CDK lo configura como `bedrock`
- ✅ `MODEL_NAME` → CDK lo configura como `anthropic.claude-3-5-sonnet-20241022-v2:0`

**Solo crea `.env` si quieres probar localmente** (para `make quick-start`):
```bash
cp .env.example .env
# Agregar solo: OPENAI_API_KEY=sk-proj-xxx  (para pruebas Docker locales)
```

---

## 🚀 Inicio Rápido

### Despliegue con Un Solo Comando

```bash
make deploy-aws
```

Este único comando:
1. ✅ Valida prerrequisitos (AWS CLI, CDK, Docker, credenciales, Bedrock)
2. ✅ Construye imágenes Docker (backend + frontend)
3. ✅ Despliega infraestructura con CDK (~10 minutos)
4. ✅ Sube imágenes a ECR
5. ✅ Carga datos iniciales en la base de datos automáticamente
6. ✅ Despliega Streamlit en App Runner
7. ✅ Devuelve todas las URLs de servicios

**Resultado esperado:**
```
╔════════════════════════════════════════════════════════════╗
║              🎉 ¡Despliegue Exitoso!                       ║
╚════════════════════════════════════════════════════════════╝

📋 Información del Despliegue:

🌐 Endpoints de Servicios:

  Frontend (Streamlit):
    https://abc123.us-east-1.awsapprunner.com

  API Backend:
    https://xyz789.execute-api.us-east-1.amazonaws.com/prod/

  Documentación API:
    https://xyz789.execute-api.us-east-1.amazonaws.com/prod/docs

🗄️ Base de Datos:

  PostgreSQL: finadvisor-xxx.us-east-1.rds.amazonaws.com:5432
  Base de datos: finadvisor
  Usuario: postgres

  Redis: finadvisor-xxx.cache.amazonaws.com:6379

📊 Datos Cargados:

  ✓ Productos (desde data/products.csv)
  ✓ Clientes (desde data/clients.csv)
  ✓ Portfolios (desde data/portfolios.csv)

🚀 Próximos Pasos:

  1. Abrir el frontend de Streamlit:
     https://abc123.us-east-1.awsapprunner.com

  2. Seleccionar un cliente (CLI001, CLI002, CLI003, CLI004)

  3. Hacer clic en 'Cargar Perfil'

  4. Comenzar a chatear: 'que productos me puedes recomendar'
```

---

## 📦 Qué Se Despliega

### Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                 INTERNET (Usuarios)                     │
└─────────────────────┬───────────────────────────────────┘
                      │
           ┌──────────┴──────────┐
           │                     │
           ▼                     ▼
   ┌───────────────┐    ┌────────────────┐
   │  App Runner   │    │  API Gateway   │
   │  (Streamlit)  │    │  (API Backend) │
   └───────┬───────┘    └────────┬───────┘
           │                     │
           │            ┌────────▼────────┐
           │            │ Función Lambda  │
           │            │ (Orquestador)   │
           │            └────────┬────────┘
           │                     │
           └─────────────────────┼─────────────┐
                        ┌────────▼────────┐    │
                        │   VPC Privada   │    │
                        │    Subnets      │    │
                        └────────┬────────┘    │
                   ┌─────────────┼──────────┐  │
                   │             │          │  │
              ┌────▼────┐   ┌───▼───┐  ┌──▼──▼──┐
              │   RDS   │   │ Redis │  │ Bedrock │
              │  (LTM)  │   │ (STM) │  │  (LLM)  │
              └─────────┘   └───────┘  └─────────┘
```

### Recursos Creados

| Servicio | Recurso | Propósito | Costo/Mes |
|---------|----------|---------|------------|
| **ECR** | 2 repositorios | Imágenes Docker (backend, frontend) | Gratis (< 500MB) |
| **App Runner** | 1 servicio | Frontend Streamlit | $10-30 |
| **Lambda** | 3 funciones | Lógica backend, servidores MCP | ~$5 |
| **API Gateway** | 1 API REST | Endpoints HTTP | ~$3.50 |
| **RDS** | PostgreSQL t3.micro | Base de datos (LTM) | ~$15 |
| **ElastiCache** | Redis t3.micro | Caché (STM) | ~$12 |
| **Bedrock** | Pago por uso | Llamadas API Claude | ~$10-50 |
| **VPC** | 1 VPC + subnets | Aislamiento de red | ~$5 (NAT) |
| **S3** | 1 bucket | Almacenamiento datos | < $1 |
| **CloudWatch** | Logs | Monitoreo | ~$5 |
| **Total** | | | **$50-100/mes** |

---

## 🔧 Pasos Manuales (Avanzado)

Si quieres desplegar paso a paso en lugar de usar `make deploy-aws`:

### 1. Bootstrap CDK (Solo Primera Vez)

```bash
cd infra
npm install
cdk bootstrap aws://ACCOUNT_ID/us-east-1
cd ..
```

### 2. Construir Imágenes Docker

```bash
docker build -t finadvisor-backend:latest -f backend/Dockerfile .
docker build -t finadvisor-frontend:latest -f frontend/Dockerfile .
```

### 3. Desplegar Infraestructura

```bash
cd infra
cdk deploy FinAdvisorStack --outputs-file ../cdk-outputs.json
cd ..
```

### 4. Subir Imágenes a ECR

```bash
# Obtener URIs de ECR desde outputs
BACKEND_ECR=$(jq -r '.FinAdvisorStack.BackendEcrRepo' cdk-outputs.json)
FRONTEND_ECR=$(jq -r '.FinAdvisorStack.FrontendEcrRepo' cdk-outputs.json)

# Login a ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Etiquetar y subir
docker tag finadvisor-backend:latest $BACKEND_ECR:latest
docker push $BACKEND_ECR:latest

docker tag finadvisor-frontend:latest $FRONTEND_ECR:latest
docker push $FRONTEND_ECR:latest
```

### 5. Cargar Datos en la Base de Datos

```bash
# Obtener endpoint de BD
DB_ENDPOINT=$(jq -r '.FinAdvisorStack.DbEndpoint' cdk-outputs.json)

# Obtener contraseña de BD desde Secrets Manager
DB_SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name FinAdvisorStack \
  --query "Stacks[0].Outputs[?OutputKey=='DbSecretArn'].OutputValue" \
  --output text)

DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id $DB_SECRET_ARN \
  --query SecretString \
  --output text | jq -r .password)

# Ejecutar script de carga
DB_HOST=$DB_ENDPOINT \
DB_PASSWORD=$DB_PASSWORD \
python3 scripts/seed_database.py
```

---

## 🔍 Monitoreo y Depuración

### Ver Logs

```bash
# Logs de Lambda (backend)
aws logs tail /aws/lambda/FinAdvisorStack-OrchestratorLambda --follow

# Logs de App Runner (frontend)
aws logs tail /aws/apprunner/finadvisor-frontend/application --follow
```

### Verificar Salud de Servicios

```bash
# Salud de API
curl https://TU_API_ENDPOINT/health

# Conexión a base de datos
PGPASSWORD=xxx psql -h TU_DB_ENDPOINT -U postgres -d finadvisor -c "SELECT COUNT(*) FROM products"

# Conexión a Redis
redis-cli -h TU_REDIS_ENDPOINT -p 6379 ping
```

### Problemas Comunes

#### 1. Acceso Denegado a Bedrock

**Error**: `AccessDeniedException: Could not access model`

**Solución**:
- Habilitar acceso a modelo Bedrock: https://console.aws.amazon.com/bedrock/home#/modelaccess
- Esperar 2-5 minutos para activación
- Verificar que la región es us-east-1

#### 2. Timeout de Conexión a Base de Datos

**Error**: `FATAL: password authentication failed`

**Solución**:
```bash
# Obtener contraseña correcta desde Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id TU_SECRET_ARN \
  --query SecretString --output text | jq -r .password
```

#### 3. App Runner No Inicia

**Error**: `Service failed to start`

**Solución**:
- Verificar logs: `aws logs tail /aws/apprunner/finadvisor-frontend/application`
- Verificar que la imagen se subió: `aws ecr describe-images --repository-name finadvisor-frontend`
- Verificar variables de entorno en stack CDK

---

## 🔄 Actualizaciones y Redespliegue

### Actualizar Código

```bash
# Actualizar y redesplegar
make update-aws

# O manualmente:
docker build -t finadvisor-backend:latest -f backend/Dockerfile .
docker build -t finadvisor-frontend:latest -f frontend/Dockerfile .

# Subir a ECR (activa auto-despliegue)
docker push $BACKEND_ECR:latest
docker push $FRONTEND_ECR:latest
```

### Actualizar Infraestructura

```bash
# Modificar infra/cdk_stack.py
# Luego:
cd infra && cdk deploy FinAdvisorStack
```

---

## 🗑️ Limpieza / Destruir

### Eliminar Todo

```bash
make destroy-aws

# O manualmente:
cd infra
cdk destroy FinAdvisorStack --force
```

Esto eliminará:
- Todas las funciones Lambda
- API Gateway
- Servicio App Runner
- Imágenes ECR
- Base de datos RDS
- Cluster Redis
- VPC y networking
- Todos los logs de CloudWatch

⚠️ **Advertencia de Pérdida de Datos**: Esto es irreversible. La base de datos y todos los datos se eliminarán permanentemente.

---

## 💰 Optimización de Costos

### Entorno Dev/Test

Para desarrollo, usar instancias más pequeñas:

```python
# En infra/cdk_stack.py

# RDS - Usar t3.micro (elegible para capa gratuita)
instance_type=ec2.InstanceType.of(
    ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
)

# Redis - Usar t3.micro
cache_node_type="cache.t3.micro"

# App Runner - Usar 0.25 vCPU / 0.5 GB
cpu="256",
memory="512",
```

### Entorno de Producción

Para producción, escalar:

```python
# RDS - Usar t3.small o t3.medium
instance_type=ec2.InstanceType.of(
    ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL
)

# Redis - Usar t3.small
cache_node_type="cache.t3.small"

# App Runner - Usar 1 vCPU / 2 GB (ya configurado)
cpu="1024",
memory="2048",
```

### Apagar Cuando No Se Use

```bash
# Pausar App Runner (ahorra ~$10-20/mes)
aws apprunner pause-service --service-arn TU_SERVICE_ARN

# Reanudar cuando sea necesario
aws apprunner resume-service --service-arn TU_SERVICE_ARN
```

---

## 🔒 Mejores Prácticas de Seguridad

### 1. Seguridad de Base de Datos

- ✅ Base de datos en subnets privadas de VPC (sin acceso público)
- ✅ Credenciales almacenadas en AWS Secrets Manager
- ✅ Encriptación en reposo habilitada
- ✅ Backups automatizados (retención de 7 días)

### 2. Seguridad de API

- Agregar autenticación con API key:
```python
# En cdk_stack.py
api_key = apigateway.ApiKey(self, "ApiKey")
usage_plan = api.add_usage_plan("UsagePlan", throttle={...})
usage_plan.add_api_key(api_key)
```

- Agregar configuración CORS si es necesario

### 3. Seguridad de Bedrock

- ✅ Rol IAM restringe acceso a modelos específicos
- ✅ Todas las solicitudes registradas en CloudWatch

---

## 📊 Monitoreo y Alertas

### Configurar Alarmas de CloudWatch

```bash
# Alarma de errores de Lambda
aws cloudwatch put-metric-alarm \
  --alarm-name FinAdvisor-Lambda-Errors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold

# Alarma de CPU de base de datos
aws cloudwatch put-metric-alarm \
  --alarm-name FinAdvisor-DB-CPU \
  --metric-name CPUUtilization \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

---

## 🎓 Próximos Pasos

Después del despliegue exitoso:

1. **Probar la Aplicación**
   - Abrir URL de Streamlit
   - Probar con los 4 clientes (CLI001-CLI004)
   - Verificar recomendaciones de portfolio

2. **Monitorear Costos**
   - Revisar AWS Cost Explorer después de 24 horas
   - Configurar alertas de facturación

3. **Personalizar**
   - Modificar prompts en `backend/agent/fintech_agent.py`
   - Agregar más productos a `data/products.csv`
   - Personalizar UI de Streamlit en `frontend/app.py`

4. **Escalar**
   - Agregar autoscaling para App Runner
   - Habilitar multi-AZ para RDS
   - Agregar CDN de CloudFront

---

## 📚 Recursos Adicionales

- [Documentación AWS CDK](https://docs.aws.amazon.com/cdk/)
- [Documentación AWS App Runner](https://docs.aws.amazon.com/apprunner/)
- [Documentación AWS Bedrock](https://docs.aws.amazon.com/bedrock/)
- [Guía de Despliegue Streamlit](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app)

---

**¿Necesitas Ayuda?**
- Revisa los logs de CloudWatch primero
- Consulta la sección de solución de problemas arriba
- Abre un issue en el repositorio

**Tiempo de Despliegue**: ~15-20 minutos
**Dificultad**: Intermedio
**Costo**: $50-100/mes (escala a casi $0 cuando no se usa)
