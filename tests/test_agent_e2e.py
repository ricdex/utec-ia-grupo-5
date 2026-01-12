"""
End-to-End tests for FinAdvisor Agent
Tests the complete flow from user input to portfolio recommendation
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.e2e
class TestFinAdvisorAgentE2E:
    """End-to-end tests for FinAdvisor agent"""

    def test_agent_initialization(self, fintech_agent):
        """Test agent can be initialized"""
        assert fintech_agent.client_id == "TEST_CLI_001"
        assert fintech_agent.memory is not None
        assert fintech_agent.system_prompt is not None

    def test_memory_manager_initialization(self, memory_manager):
        """Test memory manager initialization"""
        assert memory_manager.client_id == "TEST_CLI_001"
        assert memory_manager.stm is not None
        assert memory_manager.ltm is not None

    def test_add_message_to_stm(self, memory_manager):
        """Test adding messages to short-term memory"""
        memory_manager.add_user_message("Hello, I want to invest")
        memory_manager.add_assistant_message("Let me help you with that")

        history = memory_manager.stm.get_conversation_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_update_client_profile(self, memory_manager):
        """Test updating client profile in long-term memory"""
        memory_manager.update_client_profile(
            risk_profile="conservador",
            available_amount_usd=50000,
            investment_horizon_months=24,
        )

        profile = memory_manager.get_client_memory()
        assert profile["risk_profile"] == "conservador"
        assert profile["available_amount_usd"] == 50000
        assert profile["investment_horizon_months"] == 24

    def test_portfolio_diversification(
        self, sample_eligible_products, sample_client_profile
    ):
        """Test portfolio diversification logic"""
        from backend.utils.finance_calc import FinanceCalculator

        allocations = FinanceCalculator.diversify_portfolio(
            total_amount=sample_client_profile["available_amount_usd"],
            eligible_products=sample_eligible_products,
            client_risk_profile=sample_client_profile["risk_profile"],
            max_aggressive_pct=sample_client_profile["max_aggressive_pct"],
        )

        assert len(allocations) > 0
        total_percentage = sum(a.percentage for a in allocations)
        assert abs(total_percentage - 100) < 0.01  # Should sum to 100%

        total_amount = sum(a.amount for a in allocations)
        assert abs(total_amount - sample_client_profile["available_amount_usd"]) < 1

    def test_portfolio_metrics_calculation(self, sample_portfolio_allocation):
        """Test portfolio metrics calculation"""
        from backend.utils.finance_calc import FinanceCalculator, ProductAllocation

        allocations = [
            ProductAllocation(
                product_id=a["product_id"],
                product_name=a["product_name"],
                percentage=a["percentage"],
                amount=a["amount"],
                annual_rate=a["annual_rate"],
            )
            for a in sample_portfolio_allocation
        ]

        metrics = FinanceCalculator.calculate_portfolio_metrics(allocations)

        assert metrics.expected_return > 0
        assert metrics.expected_volatility > 0
        assert metrics.expected_liquidity in ["alta", "media", "baja"]
        # Sharpe ratio should be positive if return > risk-free rate
        assert metrics.sharpe_ratio is not None

    def test_guardrails_validation(self, sample_client_profile, sample_portfolio_allocation):
        """Test guardrails validation logic"""
        from backend.utils.guardrails import FinancialGuardrails

        is_valid, violations = FinancialGuardrails.validate_recommendation(
            sample_client_profile,
            sample_portfolio_allocation,
            expected_return=0.065,
        )

        # Should be valid
        assert isinstance(is_valid, bool)
        assert isinstance(violations, list)
        # Should have at least the mandatory disclaimer
        assert any(v.rule == "mandatory_disclaimer" for v in violations)

    def test_guardrails_high_capital_novice_escalation(self):
        """Test guardrails escalation for high capital + novice + aggressive"""
        from backend.utils.guardrails import FinancialGuardrails

        profile = {
            "risk_profile": "agresivo",
            "available_amount_usd": 150000,  # Above threshold
            "investment_experience": "low",  # Novice
            "target_return_pct": 12,
            "max_aggressive_pct": 60,
        }

        is_valid, violations = FinancialGuardrails.validate_recommendation(
            profile,
            [{"product_type": "agresivo", "percentage": 60}],
            expected_return=0.12,
        )

        # Should find escalation rule
        escalation_violations = [
            v for v in violations
            if v.rule == "high_capital_novice_aggressive"
        ]
        assert len(escalation_violations) > 0
        assert escalation_violations[0].action == "escalate"

    def test_compound_return_calculation(self):
        """Test financial compound return calculation"""
        from backend.utils.finance_calc import FinanceCalculator

        # $10,000 at 5% for 2 years
        final_amount = FinanceCalculator.calculate_final_amount(10000, 0.05, 24)

        # Should be approximately $11,050 (5% annually)
        expected = 10000 * (1.05 ** 2)
        assert abs(final_amount - expected) < 100

    def test_withdrawal_penalty_calculation(self):
        """Test withdrawal penalty logic"""
        from backend.utils.finance_calc import FinanceCalculator

        # Withdraw within penalty window
        net_amount, has_penalty = FinanceCalculator.estimate_withdrawal_penalty(
            amount=10000,
            withdrawal_time_months=3,  # 3 months
            withdrawal_window_months=6,  # Window is 6 months
            penalty_pct=2.0,  # 2% penalty
        )

        assert has_penalty is True
        assert net_amount == 9800  # 10000 - 200 penalty

        # Withdraw after window
        net_amount, has_penalty = FinanceCalculator.estimate_withdrawal_penalty(
            amount=10000,
            withdrawal_time_months=12,
            withdrawal_window_months=6,
            penalty_pct=2.0,
        )

        assert has_penalty is False
        assert net_amount == 10000

    def test_portfolio_simulation(self, sample_portfolio_allocation):
        """Test portfolio simulation under different scenarios"""
        from backend.utils.finance_calc import SimulationEngine, ProductAllocation

        allocations = [
            ProductAllocation(
                product_id=a["product_id"],
                product_name=a["product_name"],
                percentage=a["percentage"],
                amount=a["amount"],
                annual_rate=a["annual_rate"],
            )
            for a in sample_portfolio_allocation
        ]

        results = SimulationEngine.simulate_portfolio(
            allocations=allocations,
            months=24,
            scenarios=["base", "optimistic", "pessimistic"],
        )

        assert "base" in results
        assert "optimistic" in results
        assert "pessimistic" in results

        # Optimistic should have higher return than pessimistic
        assert results["optimistic"]["final_value"] > results["pessimistic"]["final_value"]

    def test_market_api_server(self, market_api_server):
        """Test market API server data retrieval"""
        indicators = market_api_server.get_market_indicators()

        assert "timestamp" in indicators
        assert "usd_rate" in indicators
        assert "inflation" in indicators
        assert "benchmarks" in indicators

    def test_market_benchmark_by_type(self, market_api_server):
        """Test market benchmark retrieval by product type"""
        for product_type in ["conservador", "moderado", "agresivo"]:
            benchmark = market_api_server.get_product_benchmark(product_type)

            assert "expected_return" in benchmark
            assert "volatility" in benchmark

            # Verify risk increases with aggressiveness
            if product_type == "conservador":
                assert benchmark["expected_return"] <= 0.06
            elif product_type == "agresivo":
                assert benchmark["expected_return"] >= 0.10

    def test_conversation_context_preservation(self, memory_manager):
        """Test that conversation context is properly preserved"""
        messages = [
            ("¿Cuál es tu perfil de riesgo?", "conservador"),
            ("¿Cuánto dinero tienes para invertir?", "$50,000"),
            ("¿Cuál es tu horizonte de inversión?", "24 meses"),
        ]

        for question, answer in messages:
            memory_manager.add_user_message(question)
            memory_manager.add_assistant_message(answer)

        context = memory_manager.get_conversation_context()

        # Context should contain recent messages
        assert "perfil" in context.lower()
        assert "dinero" in context.lower()

    def test_memory_serialization(self, memory_manager):
        """Test memory can be serialized and deserialized"""
        memory_manager.add_user_message("Test message")
        memory_manager.update_client_profile(risk_profile="conservador")

        # Serialize
        serialized = memory_manager.to_dict()

        # Deserialize
        restored = memory_manager.from_dict(serialized)

        assert restored.client_id == memory_manager.client_id
        assert len(restored.stm.messages) == len(memory_manager.stm.messages)
        assert restored.ltm.profile_data["risk_profile"] == "conservador"

    def test_disclaimer_generation(self):
        """Test disclaimer generation"""
        from backend.utils.guardrails import FinancialGuardrails

        disclaimer = FinancialGuardrails.generate_disclaimer()

        assert "AVISO" in disclaimer
        assert "recomendación educativa" in disclaimer.lower()
        assert "asesor" in disclaimer.lower()

    def test_explanation_generation(self):
        """Test educational explanation generation"""
        from backend.utils.guardrails import FinancialGuardrails

        explanation = FinancialGuardrails.generate_explanation(
            portfolio_allocation=[
                {
                    "product_name": "Fondo A",
                    "percentage": 50,
                    "amount": 25000,
                    "annual_rate": 0.05,
                    "liquidity": "media",
                }
            ],
            expected_return=0.065,
            expected_risk="medio",
            client_profile={
                "available_amount_usd": 50000,
                "investment_horizon_months": 24,
                "risk_profile": "moderado",
                "liquidity_preference": "media",
                "target_return_pct": 8.0,
                "max_aggressive_pct": 40,
            },
        )

        assert "Fondo A" in explanation
        assert "50%" in explanation or "0.5" in explanation
        assert "Diversificación" in explanation


@pytest.mark.e2e
class TestLambdaOrchestratorE2E:
    """End-to-end tests for Lambda Orchestrator"""

    @patch("backend.orchestrator.cloud.FinAdvisor")
    def test_lambda_health_endpoint(self, mock_agent):
        """Test Lambda health check endpoint"""
        from backend.orchestrator.cloud import lambda_handler

        event = {
            "httpMethod": "GET",
            "path": "/health",
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"
        assert body["service"] == "FinAdvisor"

    @patch("backend.orchestrator.cloud.FinAdvisor")
    def test_lambda_chat_endpoint(self, mock_agent_class):
        """Test Lambda chat endpoint"""
        from backend.orchestrator.cloud import lambda_handler

        # Mock the agent
        mock_agent = MagicMock()
        mock_agent.chat.return_value = "Hello, how can I help you invest?"
        mock_agent_class.return_value = mock_agent

        event = {
            "httpMethod": "POST",
            "path": "/chat",
            "body": json.dumps({
                "client_id": "TEST_CLI_001",
                "message": "I want to invest $50,000"
            })
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "response" in body
        assert body["client_id"] == "TEST_CLI_001"

    @patch("backend.orchestrator.cloud.FinAdvisor")
    def test_lambda_recommendation_endpoint(self, mock_agent_class):
        """Test Lambda recommendation endpoint"""
        from backend.orchestrator.cloud import lambda_handler

        mock_agent = MagicMock()
        mock_agent._build_portfolio.return_value = json.dumps({
            "allocations": [
                {
                    "product_id": "PROD001",
                    "product_name": "Conservative Fund",
                    "percentage": 50,
                    "amount": 25000,
                    "annual_rate": 0.05
                }
            ],
            "metrics": {
                "expected_return": 0.065,
                "expected_volatility": 0.08,
                "expected_liquidity": "media"
            }
        })
        mock_agent._validate_guardrails.return_value = json.dumps({
            "is_valid": True,
            "violations": [],
            "needs_escalation": False
        })
        mock_agent.memory = MagicMock()
        mock_agent_class.return_value = mock_agent

        event = {
            "httpMethod": "POST",
            "path": "/recommendation",
            "body": json.dumps({
                "client_id": "TEST_CLI_001",
                "amount": 50000,
                "risk_profile": "moderado",
                "months": 24,
                "target_return": 8.0
            })
        }

        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "recommendation" in body
        assert body["recommendation"]["allocations"][0]["product_id"] == "PROD001"
