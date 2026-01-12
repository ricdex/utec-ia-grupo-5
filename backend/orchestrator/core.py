"""
FinAdvisor Orchestrator - Core Logic
Shared between local (FastAPI) and cloud (Lambda) environments
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

# LangSmith tracing (optional)
try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True

    # Enable LangSmith if environment variables are set
    if os.getenv("LANGCHAIN_TRACING_V2") == "true" and os.getenv("LANGCHAIN_API_KEY"):
        logging.info("LangSmith tracing enabled")
    else:
        logging.info("LangSmith tracing disabled (LANGCHAIN_TRACING_V2 or LANGCHAIN_API_KEY not set)")
except ImportError:
    LANGSMITH_AVAILABLE = False
    logging.info("LangSmith not available (langsmith not installed)")
    # Fallback decorator
    def traceable(func):
        return func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# Optional: LLM Judge for Real-Time Evaluation
# ============================================================

def run_judge_evaluation_async(client_id: str, message: str, response: str):
    """
    Run LLM judge evaluation asynchronously (non-blocking)
    Only executes if ENABLE_JUDGE_EVAL=true in environment
    """
    if os.getenv("ENABLE_JUDGE_EVAL", "false").lower() != "true":
        return  # Judge evaluation disabled

    if not LANGSMITH_AVAILABLE:
        logger.warning("Judge evaluation skipped: LangSmith not available")
        return

    try:
        # Import evaluator
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from evaluation.llm_judge import get_llm_judge

        judge = get_llm_judge()
        if judge is None:
            logger.warning("Judge evaluation skipped: LLM judge not available")
            return

        # Create mock run/example for judge
        class MockRun:
            def __init__(self, outputs):
                self.outputs = outputs

        class MockExample:
            def __init__(self, inputs):
                self.inputs = inputs

        mock_run = MockRun({"response": response})
        mock_example = MockExample({"message": message})

        # Run judge
        result = judge(mock_run, mock_example)
        logger.info(f"Judge evaluation for {client_id}: {result}")

    except Exception as e:
        logger.error(f"Judge evaluation error: {e}")


# ============================================================
# Core Orchestrator Class (Shared)
# ============================================================

class FinAdvisorOrchestrator:
    """
    Orchestrator for FinAdvisor agent requests

    This class is SHARED between:
    - Local environment (FastAPI server)
    - Cloud environment (AWS Lambda)

    It manages agent instances and routes requests to appropriate methods.
    """

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

    @traceable(
        name="orchestrator_chat",
        run_type="chain",
        metadata={"source": "orchestrator"}
    )
    def handle_chat(self, event: Dict) -> Dict[str, Any]:
        """
        Handle chat message request (decorated for LangSmith tracing)
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

            # Optional: Run judge evaluation (async, non-blocking)
            try:
                import threading
                judge_thread = threading.Thread(
                    target=run_judge_evaluation_async,
                    args=(client_id, message, response)
                )
                judge_thread.daemon = True
                judge_thread.start()
            except Exception as e:
                logger.warning(f"Could not start judge evaluation thread: {e}")

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

    def handle_recommend(self, event: Dict) -> Dict[str, Any]:
        """
        Handle portfolio recommendation request (programmatic API)
        Path: POST /recommend
        Body: { "client_id": "...", "amount": 10000, "risk_profile": "...", "months": 24 }
        """
        try:
            body = json.loads(event.get("body", "{}"))
            client_id = body.get("client_id")
            amount = body.get("amount")
            risk_profile = body.get("risk_profile")
            months = body.get("months")
            target_return = body.get("target_return")

            if not client_id or not amount or not risk_profile or not months:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Missing required fields: client_id, amount, risk_profile, months"
                    })
                }

            agent = self.get_agent(client_id)

            # Build portfolio using tool
            recommendation = agent._execute_tool("build_portfolio", {
                "amount": amount,
                "risk_profile": risk_profile,
                "months": months
            })

            rec_data = json.loads(recommendation)

            if "error" in rec_data:
                return {
                    "statusCode": 400,
                    "body": json.dumps(rec_data)
                }

            # Validate guardrails
            guardrails = agent._execute_tool("validate_guardrails", {
                "client_profile": {
                    "risk_profile": risk_profile,
                    "available_amount_usd": amount,
                    "investment_horizon_months": months,
                    "target_return_pct": target_return or 0
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

    def handle_health(self, event: Dict) -> Dict[str, Any]:
        """
        Handle health check request
        Path: GET /health
        """
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "healthy",
                "timestamp": str(datetime.now()),
                "config": {
                    "model_provider": self.config.get("model_provider"),
                    "model_name": self.config.get("model_name")
                }
            })
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
