"""
Lambda Orchestrator for FinAdvisor
Entry point for HTTP requests
Routes to appropriate agent methods
"""

import json
import os
import logging
import sys
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.fintech_agent import FinAdvisor
from agent.memory_manager import MemoryManager
from utils.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinAdvisorOrchestrator:
    """Orchestrates Lambda requests to FinAdvisor agent"""

    def __init__(self):
        self.agents = {}  # Cache of agents by client_id
        self.config = get_config()

    def get_agent(self, client_id: str, model: str = None) -> FinAdvisor:
        """Get or create agent for client with optional model override"""
        # Use model from parameter, or use cache key with model
        agent_key = f"{client_id}_{model}" if model else client_id

        if agent_key not in self.agents:
            self.agents[agent_key] = FinAdvisor(client_id, model=model)
        return self.agents[agent_key]

    def handle_chat(self, event: Dict) -> Dict[str, Any]:
        """
        Handle chat message request
        Path: POST /chat
        Body: { "client_id": "...", "message": "...", "model_name": "..." (optional) }
        """
        try:
            body = json.loads(event.get("body", "{}"))
            client_id = body.get("client_id")
            message = body.get("message")
            model_name = body.get("model_name")  # Optional model override

            if not client_id or not message:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Missing client_id or message"
                    })
                }

            agent = self.get_agent(client_id, model=model_name)
            response = agent.chat(message)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "client_id": client_id,
                    "response": response,
                    "timestamp": str(datetime.now())
                })
            }

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)})
            }

    def handle_recommendation(self, event: Dict) -> Dict[str, Any]:
        """
        Handle portfolio recommendation request
        Path: POST /recommendation
        Body: {
            "client_id": "...",
            "amount": 50000,
            "risk_profile": "moderado",
            "months": 24,
            "target_return": 8.0
        }
        """
        try:
            body = json.loads(event.get("body", "{}"))

            client_id = body.get("client_id")
            amount = body.get("amount")
            risk_profile = body.get("risk_profile")
            months = body.get("months")
            target_return = body.get("target_return")

            if not all([client_id, amount, risk_profile, months]):
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Missing required fields: client_id, amount, risk_profile, months"
                    })
                }

            agent = self.get_agent(client_id)

            # Update client profile in agent memory
            agent.memory.update_client_profile(
                available_amount_usd=amount,
                risk_profile=risk_profile,
                investment_horizon_months=months,
                target_return_pct=target_return or 0
            )

            # Build portfolio
            recommendation = agent._build_portfolio({
                "amount": amount,
                "risk_profile": risk_profile,
                "months": months,
                "max_aggressive_pct": 40
            })

            rec_data = json.loads(recommendation)

            if "error" in rec_data:
                return {
                    "statusCode": 400,
                    "body": json.dumps(rec_data)
                }

            # Validate guardrails
            guardrails = agent._validate_guardrails({
                "client_profile": {
                    "risk_profile": risk_profile,
                    "available_amount_usd": amount,
                    "investment_horizon_months": months,
                    "target_return_pct": target_return or 0,
                    "max_aggressive_pct": 40
                },
                "portfolio_allocation": rec_data.get("allocations", []),
                "expected_return": rec_data.get("metrics", {}).get("expected_return", 0)
            })

            guardrails_data = json.loads(guardrails)

            # Save to LTM
            agent.memory.save_recommendation_to_ltm({
                "allocations": rec_data.get("allocations"),
                "metrics": rec_data.get("metrics"),
                "guardrails_status": guardrails_data
            })

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "client_id": client_id,
                    "recommendation": rec_data,
                    "guardrails": guardrails_data,
                    "timestamp": str(datetime.now())
                })
            }

        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)})
            }

    def handle_profile(self, event: Dict) -> Dict[str, Any]:
        """
        Handle client profile request
        Path: GET /profile/{client_id}
        """
        try:
            client_id = event.get("pathParameters", {}).get("client_id")

            if not client_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing client_id"})
                }

            agent = self.get_agent(client_id)
            profile = agent.memory.get_client_memory()

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "client_id": client_id,
                    "profile": profile
                })
            }

        except Exception as e:
            logger.error(f"Profile error: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)})
            }

    def handle_memory(self, event: Dict) -> Dict[str, Any]:
        """
        Handle memory request (for testing/debugging)
        Path: GET /memory/{client_id}
        """
        try:
            client_id = event.get("pathParameters", {}).get("client_id")

            if not client_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing client_id"})
                }

            agent = self.get_agent(client_id)
            memory_state = agent.memory.to_dict()

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "client_id": client_id,
                    "memory": memory_state
                })
            }

        except Exception as e:
            logger.error(f"Memory error: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)})
            }

    def handle_models(self, event: Dict) -> Dict[str, Any]:
        """
        Handle model configuration request
        Path: GET /models
        Returns list of available models
        """
        try:
            current_provider = self.config.get_model_provider()
            current_model = self.config.get_model_name()

            # Get all available models
            openai_models = self.config.get_available_models("openai")
            local_models = self.config.get_available_models("local")
            anthropic_models = self.config.get_available_models("anthropic")
            bedrock_models = self.config.get_available_models("bedrock")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "current": {
                        "provider": current_provider,
                        "model": current_model
                    },
                    "available_providers": {
                        "openai": openai_models,
                        "local": local_models,
                        "anthropic": anthropic_models,
                        "bedrock": bedrock_models
                    }
                })
            }

        except Exception as e:
            logger.error(f"Models error: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)})
            }

    def handle_config_info(self, event: Dict) -> Dict[str, Any]:
        """
        Handle config info request (for debugging)
        Path: GET /config
        Returns current configuration (without sensitive data)
        """
        try:
            return {
                "statusCode": 200,
                "body": json.dumps(self.config.to_dict())
            }

        except Exception as e:
            logger.error(f"Config error: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)})
            }


# Global orchestrator instance
orchestrator = FinAdvisorOrchestrator()


def lambda_handler(event: Dict, context: Any) -> Dict[str, Any]:
    """
    Lambda entry point
    Routes based on HTTP method and path
    """
    from datetime import datetime

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")

    logger.info(f"Request: {http_method} {path}")

    try:
        if path.startswith("/chat") and http_method == "POST":
            return orchestrator.handle_chat(event)

        elif path.startswith("/recommendation") and http_method == "POST":
            return orchestrator.handle_recommendation(event)

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
        logger.error(f"Unhandled error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }


# For local testing
if __name__ == "__main__":
    from datetime import datetime

    # Test chat endpoint
    event = {
        "httpMethod": "POST",
        "path": "/chat",
        "body": json.dumps({
            "client_id": "CLI001",
            "message": "Hola, tengo 50,000 USD para invertir"
        })
    }

    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2))
