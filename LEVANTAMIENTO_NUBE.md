# ☁️ Despliegue en AWS con Bedrock + LangSmith

Guía completa para desplegar FinAdvisor en AWS con infraestructura completamente serverless.

---

## 🎯 Resumen

Este despliegue crea una infraestructura **serverless y lista para producción** en AWS:

- **Backend**: Funciones Lambda + API Gateway
- **Frontend**: Streamlit en AWS App Runner (contenedores serverless)
- **Base de Datos**: RDS PostgreSQL (LTM - Memoria de Largo Plazo)
- **Caché**: ElastiCache Redis (STM - Memoria de Corto Plazo)
- **LLM**: AWS Bedrock (Claude 3.5 Sonnet - configurado automáticamente)
- **Guardrails**: AWS Bedrock Guardrails (cumplimiento financiero automático)
- **Trazabilidad**: LangSmith (monitoreo y debugging en producción)
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

### 2. Habilitar AWS Bedrock (Paso Manual Requerido)

⚠️ **PASO MANUAL OBLIGATORIO**: Debes habilitar el acceso a modelos de Bedrock antes del despliegue.

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

✅ **¡Listo!** Continúa al siguiente paso.

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

### 4. Configurar Archivo `.env.cloud` (Requerido)

Este archivo contiene la configuración del modelo LLM y LangSmith para producción.

**Pasos:**

1. **Crear archivo `.env.cloud`**:
   ```bash
   make env
   ```

2. **Editar `.env.cloud`** con tu configuración:
   ```bash
   nano .env.cloud
   ```

3. **Configuración mínima requerida**:

   ```bash
   # Modelo LLM (Requerido)
   MODEL_PROVIDER=bedrock
   MODEL_NAME=anthropic.claude-3-5-sonnet-20241022-v2:0
   AWS_REGION=us-east-1

   # LangSmith (Opcional pero recomendado)
   LANGCHAIN_API_KEY=lsv2_pt_tu-api-key-aqui
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=finadvisor-production

   # Guardrails
   GUARDRAILS_PROVIDER=bedrock
   AWS_BEDROCK_GUARDRAIL_VERSION=DRAFT
   ```

4. **Opciones de configuración del modelo**:

   **Opción A: AWS Bedrock (Recomendado para producción)**
   ```bash
   MODEL_PROVIDER=bedrock
   MODEL_NAME=anthropic.claude-3-5-sonnet-20241022-v2:0  # Calidad óptima
   # O: anthropic.claude-3-5-haiku-20241022-v1:0  # Más económico
   AWS_REGION=us-east-1
   ```

   **Opción B: Anthropic Direct API**
   ```bash
   MODEL_PROVIDER=anthropic
   MODEL_NAME=claude-3-5-sonnet-20241022
   ANTHROPIC_API_KEY=sk-ant-tu-api-key-aqui
   ```

   **Opción C: OpenAI**
   ```bash
   MODEL_PROVIDER=openai
   MODEL_NAME=gpt-4o
   OPENAI_API_KEY=sk-proj-tu-api-key-aqui
   ```

5. **Obtener LangSmith API key** (opcional):
   - Crear cuenta: https://smith.langchain.com
   - Obtener key: https://smith.langchain.com/settings

**Nota Importante:**
- ✅ Ahora puedes configurar el **modelo** y **provider** desde `.env.cloud`
- ✅ Puedes usar **Bedrock**, **Anthropic** o **OpenAI** en la nube
- ❌ NO necesitas configurar `DB_HOST`, `REDIS_HOST` (CDK los maneja automáticamente)
- ❌ NO necesitas AWS credentials en `.env.cloud` (Lambda tiene permisos automáticos)

---

## 🚀 Despliegue Rápido

### Opción 1: Despliegue con Un Solo Comando

```bash
# 1. Exportar variables de LangSmith (si lo configuraste)
export $(cat .env.cloud | xargs)

# 2. Desplegar todo
make deploy-aws
```

Este único comando:
1. ✅ Valida prerrequisitos (AWS CLI, CDK, Docker, credenciales, Bedrock)
2. ✅ Construye imágenes Docker (backend + frontend)
3. ✅ Despliega infraestructura con CDK (~10-15 minutos)
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
  Redis: finadvisor-xxx.cache.amazonaws.com:6379

🤖 Modelo LLM (desde .env.cloud):

  Provider: [tu MODEL_PROVIDER]
  Model: [tu MODEL_NAME]
  Region: [tu AWS_REGION]
  Guardrails: [tu GUARDRAILS_PROVIDER] (cumplimiento financiero)

📊 Trazabilidad LangSmith:

  Status: Habilitado ✓
  Project: finadvisor-production
  Dashboard: https://smith.langchain.com

🚀 Próximos Pasos:

  1. Abrir el frontend de Streamlit:
     https://abc123.us-east-1.awsapprunner.com

  2. Seleccionar un cliente (CLI001, CLI002, CLI003, CLI004)

  3. Hacer clic en 'Cargar Perfil'

  4. Comenzar a chatear: 'que productos me puedes recomendar'
```

### Opción 2: Despliegue Paso a Paso (Avanzado)

Si prefieres tener más control:

#### 1. Bootstrap CDK (Solo Primera Vez)
```bash
cd infra
npm install
cdk bootstrap aws://ACCOUNT_ID/us-east-1
cd ..
```

#### 2. Construir Imágenes Docker
```bash
docker build -t finadvisor-backend:latest -f backend/Dockerfile .
docker build -t finadvisor-frontend:latest -f frontend/Dockerfile .
```

#### 3. Exportar Variables de LangSmith
```bash
export $(cat .env.cloud | xargs)
```

#### 4. Desplegar Infraestructura
```bash
cd infra
cdk deploy FinAdvisorStack6 --outputs-file ../cdk-outputs.json
cd ..
```

#### 5. Subir Imágenes a ECR
```bash
# Obtener URIs de ECR desde outputs
BACKEND_ECR=$(jq -r '.FinAdvisorStack6.BackendEcrRepo' cdk-outputs.json)
FRONTEND_ECR=$(jq -r '.FinAdvisorStack6.FrontendEcrRepo' cdk-outputs.json)

# Login a ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Etiquetar y subir
docker tag finadvisor-backend:latest $BACKEND_ECR:latest
docker push $BACKEND_ECR:latest

docker tag finadvisor-frontend:latest $FRONTEND_ECR:latest
docker push $FRONTEND_ECR:latest
```

#### 6. Cargar Datos en la Base de Datos
```bash
# Obtener endpoint de BD
DB_ENDPOINT=$(jq -r '.FinAdvisorStack6.DbEndpoint' cdk-outputs.json)

# Obtener contraseña de BD desde Secrets Manager
DB_SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name FinAdvisorStack6 \
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
           └─────────────────────┼─────────────────────┐
                        ┌────────▼────────┐            │
                        │   VPC Privada   │            │
                        │    Subnets      │            │
                        └────────┬────────┘            │
                   ┌─────────────┼──────────┐          │
                   │             │          │          │
              ┌────▼────┐   ┌───▼───┐  ┌──▼──────────▼──────┐
              │   RDS   │   │ Redis │  │     AWS Bedrock    │
              │  (LTM)  │   │ (STM) │  ├────────────────────┤
              └─────────┘   └───────┘  │ Claude 3.5 (LLM)   │
                                       │ Guardrails (Reglas)│
                                       └────────────────────┘
                                                │
                                       ┌────────▼────────┐
                                       │   LangSmith     │
                                       │  (Trazabilidad) │
                                       └─────────────────┘
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
| **Bedrock Guardrails** | 1 guardrail | Cumplimiento financiero | Gratis (incluido) |
| **VPC** | 1 VPC + subnets | Aislamiento de red | ~$5 (NAT) |
| **S3** | 1 bucket | Almacenamiento datos | < $1 |
| **CloudWatch** | Logs | Monitoreo | ~$5 |
| **Total** | | | **$50-100/mes** |

---

## 🛡️ Bedrock Guardrails - Cumplimiento Financiero

El stack de CDK crea automáticamente un **Bedrock Guardrail** con políticas específicas para asesoría financiera:

### Políticas Configuradas:

**1. Filtros de Contenido** (Content Filters)
- ❌ Odio y lenguaje abusivo (HIGH)
- ❌ Insultos (MEDIUM)
- ❌ Contenido sexual (HIGH)
- ❌ Violencia (MEDIUM)
- ❌ Mala conducta (HIGH)

**2. Filtros de Temas Prohibidos** (Topic Filters)
- ❌ **Retornos Garantizados**: Promesas de rendimiento sin riesgo
- ❌ **Inversiones No Autorizadas**: Criptomonedas, forex no regulado, esquemas piramidales
- ❌ **Predicciones Especulativas**: Market timing o predicciones específicas
- ❌ **Evasión Fiscal**: Consejos de evasión o fraude tributario
- ❌ **Información Privilegiada**: Insider trading

**3. Palabras Bloqueadas** (Word Filters)
- ❌ "garantizado", "garantizada"
- ❌ "sin riesgo"
- ❌ "100% seguro"
- ❌ "ganancias aseguradas"
- ❌ "retorno garantizado"
- ❌ Profanidad (lista administrada por AWS)

**4. Protección de Información Sensible** (PII Protection)
- 🔒 Email → Anonimizado
- 🔒 Teléfono → Anonimizado
- 🔒 Tarjetas de crédito → Bloqueado
- 🔒 SSN/Tax ID → Bloqueado
- 🔒 Direcciones → Anonimizado
- 🔒 Nombres → Anonimizado

**Configuración:**
- El Guardrail se crea automáticamente en el deployment
- ID del Guardrail se pasa al Lambda via variable de entorno
- Validación ocurre en cada recomendación de portafolio
- Fallback automático a validación local si Bedrock falla

**Mensajes de Bloqueo:**
- Input bloqueado: *"Lo siento, no puedo procesar esa solicitud por cumplimiento normativo financiero."*
- Output bloqueado: *"Lo siento, no puedo proporcionar esa información por restricciones de cumplimiento."*

---

## 📊 Monitoreo con LangSmith

### ¿Qué se traza en LangSmith?

Cuando habilitas LangSmith, todas las conversaciones en producción se registran automáticamente:

- ✅ **Todas las llamadas al LLM** (input/output completo)
- ✅ **Tiempos de respuesta** de cada paso
- ✅ **Tokens consumidos** por llamada
- ✅ **Errores y excepciones**
- ✅ **Cadenas completas de razonamiento** del agente
- ✅ **Herramientas (tools) utilizadas** por el agente
- ✅ **Contexto del RAG** (productos recuperados)

### Acceder al Dashboard

1. Ve a: https://smith.langchain.com
2. Busca el proyecto: "finadvisor-production"
3. Verás todas las trazas en tiempo real

### Configuración en el CDK

El stack automáticamente pasa las variables de LangSmith al Lambda:

```python
environment={
    # ... otras variables ...

    # LangSmith tracing (leídas de .env.cloud via os.getenv)
    "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2", "false"),
    "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY", ""),
    "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT", "finadvisor-production"),
}
```

### Deshabilitar Trazabilidad

Si no quieres usar LangSmith:

1. No configures `.env.cloud`
2. O edita `.env.cloud` y establece:
   ```bash
   LANGCHAIN_TRACING_V2=false
   ```
3. Exporta las variables y redespliega:
   ```bash
   export $(cat .env.cloud | xargs)
   cd infra && cdk deploy
   ```

---

## 🔍 Monitoreo y Depuración

### Ver Logs

```bash
# Logs de Lambda (backend)
aws logs tail /aws/lambda/FinAdvisorStack6-OrchestratorLambda --follow

# Logs de App Runner (frontend)
aws logs tail /aws/apprunner/finadvisor-frontend/application --follow
```

### Verificar Salud de Servicios

```bash
# Salud de API
curl https://TU_API_ENDPOINT/health
```

### Verificar Datos Cargados (Acceso Público)

**NOTA**: PostgreSQL y Redis están configurados con acceso público para facilitar la verificación de datos. Esto es útil para debugging pero en producción debería estar en subnets privadas.

#### Obtener Credenciales de PostgreSQL

```bash
# Obtener endpoint de la base de datos
DB_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name FinAdvisorStack6 \
  --query "Stacks[0].Outputs[?OutputKey=='DbEndpoint'].OutputValue" \
  --output text)

# Obtener ARN del secret
DB_SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name FinAdvisorStack6 \
  --query "Stacks[0].Outputs[?OutputKey=='DbSecretArn'].OutputValue" \
  --output text)

# Obtener contraseña
DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id "$DB_SECRET_ARN" \
  --query SecretString \
  --output text | jq -r .password)

echo "Endpoint: $DB_ENDPOINT"
echo "Password: $DB_PASSWORD"
```

#### Conectar a PostgreSQL desde tu Máquina Local

```bash
# Conectar con psql
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U postgres -d finadvisor

# O verificar datos directamente
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U postgres -d finadvisor << EOF
-- Verificar productos cargados
SELECT COUNT(*) as total_productos FROM products;

-- Verificar clientes cargados
SELECT COUNT(*) as total_clientes FROM clients;

-- Verificar portafolios cargados
SELECT COUNT(*) as total_portfolios FROM portfolios;

-- Ver algunos productos
SELECT product_id, name, category, risk_level FROM products LIMIT 5;
EOF
```

#### Conectar a Redis desde tu Máquina Local

```bash
# Obtener endpoint de Redis
REDIS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name FinAdvisorStack6 \
  --query "Stacks[0].Outputs[?OutputKey=='RedisEndpoint'].OutputValue" \
  --output text)

REDIS_PORT=$(aws cloudformation describe-stacks \
  --stack-name FinAdvisorStack6 \
  --query "Stacks[0].Outputs[?OutputKey=='RedisPort'].OutputValue" \
  --output text)

echo "Redis: $REDIS_ENDPOINT:$REDIS_PORT"

# Conectar con redis-cli (requiere tener redis-cli instalado localmente)
redis-cli -h "$REDIS_ENDPOINT" -p "$REDIS_PORT"

# Verificar que Redis está funcionando
redis-cli -h "$REDIS_ENDPOINT" -p "$REDIS_PORT" ping
# Debería responder: PONG

# Ver todas las keys (para verificar sesiones)
redis-cli -h "$REDIS_ENDPOINT" -p "$REDIS_PORT" KEYS "*"
```

#### Instalar Herramientas de Cliente (si no las tienes)

```bash
# PostgreSQL client (psql)
# macOS:
brew install postgresql

# Ubuntu/Debian:
sudo apt-get install postgresql-client

# Redis client (redis-cli)
# macOS:
brew install redis

# Ubuntu/Debian:
sudo apt-get install redis-tools
```

### Problemas Comunes

#### 1. Acceso Denegado a Bedrock

**Error**: `AccessDeniedException: Could not access model`

**Solución**:
- Habilitar acceso a modelo Bedrock: https://console.aws.amazon.com/bedrock/home#/modelaccess
- Esperar 2-5 minutos para activación
- Verificar que la región es us-east-1

#### 2. No veo trazas en LangSmith

**Solución**:
- Verifica que `LANGCHAIN_TRACING_V2=true` en `.env.cloud`
- Verifica que exportaste las variables: `export $(cat .env.cloud | xargs)`
- Redespliega: `cd infra && cdk deploy`
- Revisa los logs de Lambda para ver si hay errores

#### 3. Timeout de Conexión a Base de Datos

**Error**: `FATAL: password authentication failed`

**Solución**:
```bash
# Obtener contraseña correcta desde Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id TU_SECRET_ARN \
  --query SecretString --output text | jq -r .password
```

#### 4. App Runner No Inicia

**Error**: `Service failed to start`

**Solución**:
- Verificar logs: `aws logs tail /aws/apprunner/finadvisor-frontend/application`
- Verificar que la imagen se subió: `aws ecr describe-images --repository-name finadvisor-frontend`
- Verificar variables de entorno en stack CDK

---

## 🔄 Actualizaciones

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
export $(cat .env.cloud | xargs)
cd infra && cdk deploy FinAdvisorStack6
```

---

## 🗑️ Limpieza / Destruir

### Eliminar Todo

```bash
make destroy-aws

# O manualmente:
cd infra
cdk destroy FinAdvisorStack6 --force
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

### Apagar Cuando No Se Use

```bash
# Pausar App Runner (ahorra ~$10-20/mes)
aws apprunner pause-service --service-arn TU_SERVICE_ARN

# Reanudar cuando sea necesario
aws apprunner resume-service --service-arn TU_SERVICE_ARN
```

---

## 🔒 Mejores Prácticas de Seguridad

### Seguridad de Base de Datos

- ✅ Base de datos en subnets privadas de VPC (sin acceso público)
- ✅ Credenciales almacenadas en AWS Secrets Manager
- ✅ Encriptación en reposo habilitada
- ✅ Backups automatizados (retención de 7 días)

### Seguridad de API

Agregar autenticación con API key:
```python
# En cdk_stack.py
api_key = apigateway.ApiKey(self, "ApiKey")
usage_plan = api.add_usage_plan("UsagePlan", throttle={...})
usage_plan.add_api_key(api_key)
```

### Seguridad de Bedrock

- ✅ Rol IAM restringe acceso a modelos específicos
- ✅ Todas las solicitudes registradas en CloudWatch
- ✅ Guardrails automáticos para cumplimiento

---

## 📚 Resumen de Archivos de Configuración

**Para desarrollo local:**
- Archivo: `.env.local`
- Contenido: Todo (PostgreSQL, Redis, OpenAI/Bedrock/Anthropic, LangSmith)
- Uso: `make quick-start`

**Para despliegue en AWS:**
- Archivo: `.env.cloud`
- Contenido:
  - ✅ **Modelo LLM** (provider, name, API keys)
  - ✅ **AWS Region** (para Bedrock)
  - ✅ **LangSmith** (API key, tracing, project)
  - ✅ **Guardrails** (provider, version)
- Uso: `export $(cat .env.cloud | xargs) && make deploy-aws`

**Variables configurables en `.env.cloud`:**
- ✅ `MODEL_PROVIDER` → bedrock, anthropic, openai
- ✅ `MODEL_NAME` → Modelo específico según provider
- ✅ `AWS_REGION` → Región de AWS (default: us-east-1)
- ✅ `OPENAI_API_KEY` → Solo si usas OpenAI
- ✅ `ANTHROPIC_API_KEY` → Solo si usas Anthropic directo
- ✅ `LANGCHAIN_API_KEY` → Para trazabilidad
- ✅ `GUARDRAILS_PROVIDER` → bedrock o local

**Lo que NO necesitas configurar en `.env.cloud`:**
- ❌ `DB_HOST`, `DB_PORT`, `DB_PASSWORD` → CDK lo maneja automáticamente
- ❌ `REDIS_HOST`, `REDIS_PORT` → CDK lo maneja automáticamente
- ❌ `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` → Lambda tiene permisos automáticos
- ❌ `AWS_BEDROCK_GUARDRAIL_ID` → CDK lo crea automáticamente

---

**Tiempo de Despliegue**: ~15-20 minutos
**Dificultad**: Intermedio
**Costo**: $50-100/mes (escala a casi $0 cuando no se usa)
