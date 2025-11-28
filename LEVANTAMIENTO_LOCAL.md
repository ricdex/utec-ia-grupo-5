# 🚀 Levantamiento Local

Ejecutar FinAdvisor en tu máquina con Ollama (Llama 3.2).

---

## 📋 Setup (5 minutos)

### 1. Prerequisitos
```bash
git clone https://github.com/utec/utec-ia-grupo-5.git
cd utec-ia-grupo-5

# Verificar Python 3.10+
python --version
```

### 2. Crear .env
```bash
make env

# Editar .env (agregar si es necesario):
# MODEL_PROVIDER=local
# MODEL_NAME=llama2
# OLLAMA_BASE_URL=http://localhost:11434
```

### 3. Instalar y Levantar
```bash
make install
make up
```

### 4. Descargar Modelo
```bash
# En Terminal 1: Descargar Llama 3.2
make ollama-pull

# Esperar a que termine (~2-5 minutos, 4GB)
```

### 5. Cargar Datos (PostgreSQL + RAG)
```bash
make seed
# Carga automaticamente:
# - Esquema PostgreSQL + 8 productos sample + 4 clientes
# - RAG con descripciones de productos + composición
```

### 6. Iniciar Backend (Terminal 2)
```bash
make backend
# API en http://localhost:8000
```

### 7. Iniciar Frontend (Terminal 3)
```bash
make frontend
# UI en http://localhost:8501
```

---

## ✅ Verificación

```bash
# Health check
curl http://localhost:8000/health

# Ver modelos cargados
make ollama-list

# Chat con Llama
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "CLI001",
    "message": "Hola, tengo $50k para invertir"
  }'
```

---

## 📊 Servicios

| Servicio | URL | Comando |
|----------|-----|---------|
| Ollama | http://localhost:11434 | `make ollama-list` |
| PostgreSQL | localhost:5432 | `make db-connect` |
| Redis | localhost:6379 | `make redis-cli` |
| Backend | http://localhost:8000 | `make backend` |
| Frontend | http://localhost:8501 | `make frontend` |

---

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| Ollama lento | `make ollama-pull` y esperar |
| API no responde | `make backend` |
| Datos no cargados | `make seed` |
| PostgreSQL error | `make down && make up && make health` |

---

## 🧹 Limpiar

```bash
make down      # Detener servicios
make clean     # Limpiar todo
```

---

**Ver arquitectura:** [README.md](./README.md)
