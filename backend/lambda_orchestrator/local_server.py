#!/usr/bin/env python3
"""
Local FastAPI server for FinAdvisor Lambda Orchestrator
Allows running Lambda locally during development
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from handler import lambda_handler
from datetime import datetime

# Create FastAPI app
app = FastAPI(
    title="FinAdvisor API",
    description="AI-Powered Financial Advisory Agent",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Convert Lambda event to FastAPI request
def create_lambda_event(request_path: str, method: str, body: dict = None, path_params: dict = None):
    """Create Lambda event from FastAPI request"""
    event = {
        "httpMethod": method,
        "path": request_path,
        "body": json.dumps(body) if body else None,
        "pathParameters": path_params or {},
        "queryStringParameters": {},
        "headers": {},
    }
    return event


# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    event = create_lambda_event("/health", "GET")
    response = lambda_handler(event, None)
    return JSONResponse(
        content=json.loads(response.get("body", "{}")),
        status_code=response.get("statusCode", 200)
    )


@app.post("/chat")
async def chat(request: Request):
    """Chat endpoint"""
    body = await request.json()
    event = create_lambda_event("/chat", "POST", body)
    response = lambda_handler(event, None)

    return JSONResponse(
        content=json.loads(response.get("body", "{}")),
        status_code=response.get("statusCode", 200)
    )


@app.post("/recommendation")
async def recommendation(request: Request):
    """Recommendation endpoint"""
    body = await request.json()
    event = create_lambda_event("/recommendation", "POST", body)
    response = lambda_handler(event, None)

    return JSONResponse(
        content=json.loads(response.get("body", "{}")),
        status_code=response.get("statusCode", 200)
    )


@app.get("/profile/{client_id}")
async def get_profile(client_id: str):
    """Profile endpoint"""
    event = create_lambda_event(f"/profile/{client_id}", "GET", path_params={"client_id": client_id})
    response = lambda_handler(event, None)

    return JSONResponse(
        content=json.loads(response.get("body", "{}")),
        status_code=response.get("statusCode", 200)
    )


@app.get("/memory/{client_id}")
async def get_memory(client_id: str):
    """Memory endpoint"""
    event = create_lambda_event(f"/memory/{client_id}", "GET", path_params={"client_id": client_id})
    response = lambda_handler(event, None)

    return JSONResponse(
        content=json.loads(response.get("body", "{}")),
        status_code=response.get("statusCode", 200)
    )


@app.get("/models")
async def get_models():
    """Get available models endpoint"""
    event = create_lambda_event("/models", "GET")
    response = lambda_handler(event, None)

    return JSONResponse(
        content=json.loads(response.get("body", "{}")),
        status_code=response.get("statusCode", 200)
    )


@app.get("/config")
async def get_config():
    """Get configuration endpoint"""
    event = create_lambda_event("/config", "GET")
    response = lambda_handler(event, None)

    return JSONResponse(
        content=json.loads(response.get("body", "{}")),
        status_code=response.get("statusCode", 200)
    )


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    print("🚀 FinAdvisor Local Server")
    print("=" * 50)
    print("")
    print("🌐 API disponible en: http://localhost:8000")
    print("📚 Documentación en: http://localhost:8000/docs")
    print("")
    print("Endpoints:")
    print("  GET  /health              - Service health check")
    print("  GET  /models              - List available models")
    print("  GET  /config              - Configuration info")
    print("  POST /chat                - Chat with agent (model_name optional)")
    print("  POST /recommendation      - Get portfolio recommendation")
    print("  GET  /profile/{client_id} - Get client profile")
    print("  GET  /memory/{client_id}  - Get client memory (debug)")
    print("")

    uvicorn.run(
        "local_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
