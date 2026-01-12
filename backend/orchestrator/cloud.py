"""
FinAdvisor Cloud Orchestrator - AWS Lambda Entry Point
Cloud-specific code for AWS Lambda deployment
"""

import json
import logging
from typing import Dict, Any

from orchestrator.core import FinAdvisorOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global orchestrator instance (reused across Lambda invocations)
orchestrator = FinAdvisorOrchestrator()


def lambda_handler(event: Dict, context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point
    Routes HTTP requests based on method and path

    This function is ONLY used in cloud (AWS Lambda).
    For local development, use orchestrator/local.py instead.

    Args:
        event: Lambda event dict with httpMethod, path, body, etc.
        context: Lambda context object

    Returns:
        Dict with statusCode and body (API Gateway format)
    """
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")

    logger.info(f"Lambda Request: {http_method} {path}")

    try:
        # Route to appropriate handler
        if path.startswith("/chat") and http_method == "POST":
            return orchestrator.handle_chat(event)

        elif path.startswith("/recommendation") and http_method == "POST":
            return orchestrator.handle_recommend(event)

        elif path.startswith("/profile") and http_method == "GET":
            return orchestrator.handle_profile(event)

        elif path.startswith("/memory") and http_method == "GET":
            return orchestrator.handle_memory(event)

        elif path == "/models" and http_method == "GET":
            return orchestrator.handle_models(event)

        elif path == "/config" and http_method == "GET":
            return orchestrator.handle_config_info(event)

        elif path == "/" or path == "/health":
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "healthy",
                    "service": "FinAdvisor",
                    "version": "1.0.0",
                    "environment": "cloud (AWS Lambda)",
                    "available_endpoints": [
                        "GET /health - Service health check",
                        "GET /models - List available models",
                        "GET /config - Configuration info",
                        "POST /chat - Chat with agent (client_id, message, model_name optional)",
                        "POST /recommendation - Get portfolio recommendation",
                        "GET /profile/{client_id} - Get client profile",
                        "GET /memory/{client_id} - Get client memory"
                    ]
                })
            }

        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Endpoint not found"})
            }

    except Exception as e:
        logger.error(f"Unhandled Lambda error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }


# For local testing of Lambda handler
if __name__ == "__main__":
    # Test chat endpoint
    test_event = {
        "httpMethod": "POST",
        "path": "/chat",
        "body": json.dumps({
            "client_id": "CLI001",
            "message": "Hola, tengo 50,000 USD para invertir"
        })
    }

    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
