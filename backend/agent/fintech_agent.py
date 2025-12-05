"""
FinAdvisor Goal-Based Reflex Agent
Orchestrates portfolio recommendations using LLM, MCP tools, RAG, and memory
"""

import json
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import asdict

from agent.memory_manager import MemoryManager
from agent.rag_manager import RAGManager, RAGProductDatabase
from utils.finance_calc import FinanceCalculator, SimulationEngine, ProductAllocation
from utils.guardrails import FinancialGuardrails, GuardrailViolation
from utils.config import get_config
from utils.llm_client import LLMClientFactory
from mcp_servers.postgres_server import PostgreSQLServer
from mcp_servers.market_api_server import MarketAPIServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinAdvisor:
    """
    Goal-Based Reflex Agent for Financial Advisory
    Implements agentic reasoning with LLM, tools, and memory
    """

    def __init__(self, client_id: str, model: str = None):
        self.client_id = client_id

        # Get config
        config = get_config()

        # Get model from parameter or config
        if model is None:
            self.model = config.get_model_name()
        else:
            self.model = model

        # Get provider
        self.provider = config.get_model_provider()

        logger.info(f"FinAdvisor initialized with model: {self.model} (provider: {self.provider})")

        # Initialize LLM client based on provider
        self.llm_client = LLMClientFactory.create_from_config(config)

        # Initialize tools
        db_config = config.get_db_config()
        self.db_server = PostgreSQLServer(**db_config)
        self.market_server = MarketAPIServer()

        # Initialize RAG (empty - data loaded via seed_rag.py)
        self.rag = RAGManager()
        self.rag = RAGProductDatabase.initialize_empty(self.rag)

        # Initialize memory
        self.memory = MemoryManager(client_id)

        # System prompt with context
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt for Goal-Based Reflex Agent"""
        return """
Eres FinAdvisor, un agente asesor financiero que actúa como un Goal-Based Reflex Agent.

## Rol:
Proporcionar recomendaciones de portafolio diversificado basadas en:
1. El perfil del cliente (riesgo, horizonte, objetivos)
2. Los productos disponibles en la base de datos
3. Condiciones del mercado
4. Cumplimiento de metas financieras duras y blandas

## Proceso de Razonamiento (Estado → Acción → Estado'):

### 1. Estado Inicial (State):
- Recibe información del cliente: monto, perfil riesgo, horizonte, metas
- Consulta productos elegibles de la BD
- Obtiene contexto del mercado

### 2. Definir Metas (Goals):
- Meta dura: Retorno esperado ≥ objetivo del cliente
- Meta dura: Riesgo aceptado según perfil
- Meta dura: Límite de productos agresivos respetado
- Meta blanda: Preferencia de liquidez
- Meta blanda: Diversificación

### 3. Acciones Posibles (Actions):
- Simular diferentes combinaciones de productos
- Validar restricciones de cada portafolio
- Calcular métricas (retorno, riesgo, liquidez, Sharpe)

### 4. Simulación (Transition):
- Para cada acción, calcula: T(S, a) → S'
- Verifica cumplimiento de metas
- Compara escenarios (base, optimista, pesimista)

### 5. Decisión (Decision):
- Selecciona acción que mejor cumple metas
- Genera explicación educativa
- Aplica guardrails (disclaimers, límites de riesgo)

### 6. Estado Futuro (State'):
- Portafolio recomendado con justificación
- Métricas de desempeño esperado
- Próximos pasos y revisión periódica

## Guardrails Obligatorios:
- Disclaimer en cada recomendación
- Respetar límites por perfil (ej: conservador ≤ 20% agresivo)
- Escalada a humano si: datos insuficientes, riesgo alto + capital alto + novato
- Validar suficiencia de datos (una repregunta si es necesario)

## Capacidades de Consulta:
Cuando el usuario pregunte:
1. "¿cuales son los productos que tengo hasta ahora?" → Usa get_client_contracted_products
2. "¿cual es el capital que tengo invertido?" → Usa get_client_invested_capital
3. "¿que productos me recomiendas?" → Usa build_portfolio + validar con guardrails
4. "¿como va el mercado de mis productos?" → Usa get_product_market_data para obtener NASDAQ/precios

## Estilo de Comunicación:
- Español neutro LATAM
- Profesional, empático, educativo
- TL;DR primero, detalle bajo demanda
- Respuestas cortas sin promesas de rentabilidad
- Educación sobre conceptos financieros

## Herramientas Disponibles:
- query_eligible_products: Buscar productos por criterios
- get_client_profile: Obtener perfil del cliente
- get_client_contracted_products: Ver productos contratados del cliente
- get_client_invested_capital: Ver capital invertido del cliente
- get_market_indicators: Datos del mercado
- get_economic_calendar: Eventos económicos relevantes
- get_product_market_data: NASDAQ/precios de productos con exposición accionaria
- build_portfolio: Construir portafolio recomendado
- validate_guardrails: Validar límites de riesgo

No ejecutas operaciones reales. Requieres confirmación humana para cualquier inversión.
        """

    def chat(self, user_message: str) -> str:
        """
        Main chat method - implements agentic loop with tools
        """

        # Add to STM
        self.memory.add_user_message(user_message)

        # Build messages for LLM
        messages = self._prepare_messages()

        # Agentic loop
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Iteration {iteration}: Calling LLM")

            response = self.llm_client.create_message(
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt,
                messages=messages
            )

            # Check if we need to use tools
            if response.stop_reason == "tool_use":
                # Process tool calls
                assistant_message = response.content
                messages.append({"role": "assistant", "content": assistant_message})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_result = self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result
                        })

                # Add tool results to messages
                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                # Agent finished reasoning
                final_response = ""
                if response.content:
                    content_block = response.content[0]
                    try:
                        # Try object attribute first (Anthropic)
                        final_response = content_block.text
                    except AttributeError:
                        # Fallback to dict access (Ollama/Bedrock)
                        final_response = content_block.get("text", "")
                self.memory.add_assistant_message(final_response)
                return final_response
            else:
                # Unexpected stop reason
                break

        logger.warning("Max iterations reached")
        return "Necesito más información para hacer una recomendación. ¿Puedes clarificar tu situación financiera?"

    def _prepare_messages(self) -> List[Dict]:
        """Prepare conversation messages with context"""

        messages = []

        # Add conversation context
        conv_context = self.memory.get_conversation_context()
        if conv_context:
            messages.append({
                "role": "user",
                "content": f"[Contexto de conversación anterior]\n{conv_context}\n\n[Nuevo mensaje del usuario arriba]"
            })

        # Add recent messages
        for msg in self.memory.stm.get_conversation_history(last_n=5):
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        return messages

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Execute tool and return result"""

        try:
            if tool_name == "query_eligible_products":
                try:
                    self.db_server.connect()
                    products = self.db_server.query_eligible_products(
                        amount=tool_input.get("amount", 50000),
                        risk_profile=tool_input.get("risk_profile", "moderado"),
                        months=tool_input.get("months", 24)
                    )
                    self.db_server.close()
                    return json.dumps(products)
                except Exception as e:
                    logger.error(f"DB Error: {e}")
                    return json.dumps([])

            elif tool_name == "get_client_profile":
                try:
                    self.db_server.connect()
                    profile = self.db_server.get_client_profile(self.client_id)
                    self.db_server.close()

                    # Merge with memory
                    profile.update(self.memory.get_client_memory())
                    return json.dumps(profile)
                except Exception as e:
                    logger.error(f"Profile fetch error: {e}")
                    return json.dumps(self.memory.get_client_memory())

            elif tool_name == "get_market_indicators":
                indicators = self.market_server.get_market_indicators()
                return json.dumps(indicators)

            elif tool_name == "get_economic_calendar":
                calendar = self.market_server.get_economic_calendar()
                return json.dumps(calendar)

            elif tool_name == "get_client_contracted_products":
                try:
                    self.db_server.connect()
                    products = self.db_server.get_client_contracted_products(self.client_id)
                    self.db_server.close()
                    return json.dumps(products)
                except Exception as e:
                    logger.error(f"Error getting contracted products: {e}")
                    return json.dumps({"error": str(e), "products": []})

            elif tool_name == "get_client_invested_capital":
                try:
                    self.db_server.connect()
                    capital = self.db_server.get_client_invested_capital(self.client_id)
                    self.db_server.close()
                    return json.dumps(capital)
                except Exception as e:
                    logger.error(f"Error getting invested capital: {e}")
                    return json.dumps({"error": str(e), "total_invested_capital": 0})

            elif tool_name == "get_product_market_data":
                product_names = tool_input.get("product_names")
                market_data = self.market_server.get_product_market_data(product_names)
                return json.dumps(market_data)

            elif tool_name == "build_portfolio":
                # Internal tool for portfolio building
                return self._build_portfolio(tool_input)

            elif tool_name == "validate_guardrails":
                return self._validate_guardrails(tool_input)

            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return json.dumps({"error": str(e)})

    def _build_portfolio(self, params: Dict) -> str:
        """
        Internal tool to build portfolio recommendation
        Uses real product data without simulations
        """

        try:
            # Get eligible products from database
            self.db_server.connect()
            products = self.db_server.query_eligible_products(
                amount=params.get("amount", 50000),
                risk_profile=params.get("risk_profile", "moderado"),
                months=params.get("months", 24)
            )
            self.db_server.close()

            if not products:
                return json.dumps({
                    "error": "No eligible products found",
                    "recommendation": None
                })

            # Create diversified allocation using real product data
            allocations = FinanceCalculator.diversify_portfolio(
                total_amount=params["amount"],
                eligible_products=products,
                client_risk_profile=params.get("risk_profile", "moderado"),
                max_aggressive_pct=params.get("max_aggressive_pct", 40)
            )

            # Calculate portfolio metrics based on real product data
            metrics = FinanceCalculator.calculate_portfolio_metrics(allocations)

            # Build recommendation with real data (NO SIMULATIONS)
            recommendation = {
                "allocations": [
                    {
                        "product_id": a.product_id,
                        "product_name": a.product_name,
                        "percentage": a.percentage,
                        "amount": a.amount,
                        "annual_rate": a.annual_rate,
                        "volatility_pct": a.volatility if hasattr(a, 'volatility') else 0
                    }
                    for a in allocations
                ],
                "metrics": {
                    "expected_return": metrics.expected_return,
                    "expected_volatility": metrics.expected_volatility,
                    "expected_liquidity": metrics.expected_liquidity,
                    "sharpe_ratio": metrics.sharpe_ratio
                },
                "data_source": "Real product data from database",
                "note": "No simulations - uses actual product characteristics"
            }

            return json.dumps(recommendation)

        except Exception as e:
            logger.error(f"Portfolio build error: {e}")
            return json.dumps({"error": str(e)})

    def _validate_guardrails(self, params: Dict) -> str:
        """Validate recommendation against guardrails"""

        try:
            client_profile = params.get("client_profile", {})
            portfolio_allocation = params.get("portfolio_allocation", [])
            expected_return = params.get("expected_return", 0)

            is_valid, violations = FinancialGuardrails.validate_recommendation(
                client_profile,
                portfolio_allocation,
                expected_return
            )

            needs_escalation = FinancialGuardrails.needs_human_escalation(violations)
            disclaimer = FinancialGuardrails.generate_disclaimer()

            return json.dumps({
                "is_valid": is_valid,
                "violations": [
                    {
                        "severity": v.severity,
                        "rule": v.rule,
                        "message": v.message,
                        "action": v.action
                    }
                    for v in violations
                ],
                "needs_escalation": needs_escalation,
                "disclaimer": disclaimer
            })

        except Exception as e:
            logger.error(f"Guardrail validation error: {e}")
            return json.dumps({"error": str(e)})

    def process_conversation(self) -> Dict:
        """
        High-level method for processing a complete conversation
        Returns comprehensive recommendation or error
        """

        # Start conversation
        initial_response = self.chat("Necesito ayuda para invertir mi dinero. ¿Cuál es el primer paso?")
        logger.info(f"Initial response: {initial_response}")

        # Could continue with more interactions
        # final_response = self.chat("Tengo $50,000 USD y puedo esperar 24 meses")

        return {
            "client_id": self.client_id,
            "conversation": self.memory.stm.messages,
            "client_profile": self.memory.get_client_memory(),
            "last_response": initial_response
        }


if __name__ == "__main__":
    # Test the agent
    agent = FinAdvisor(client_id="CLI001")
    result = agent.chat("Hola, tengo 50,000 USD para invertir a 24 meses. Mi perfil es moderado.")
    print("Response:", result)
