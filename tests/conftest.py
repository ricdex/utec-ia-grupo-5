"""
Pytest configuration and fixtures for E2E tests
"""

import pytest
import json
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from agent.fintech_agent import FinAdvisor
from agent.memory_manager import MemoryManager
from utils.finance_calc import FinanceCalculator
from mcp_servers.market_api_server import MarketAPIServer


@pytest.fixture
def sample_client_id():
    """Fixture for test client ID"""
    return "TEST_CLI_001"


@pytest.fixture
def fintech_agent(sample_client_id):
    """Fixture for FinAdvisor agent instance"""
    # Mock Anthropic client for testing
    agent = FinAdvisor(sample_client_id)
    return agent


@pytest.fixture
def memory_manager(sample_client_id):
    """Fixture for memory manager"""
    memory = MemoryManager(sample_client_id)
    return memory


@pytest.fixture
def sample_eligible_products():
    """Fixture for sample products"""
    return [
        {
            "id": "PROD001",
            "name": "Fondo Conservador A",
            "type": "conservador",
            "annual_rate": 0.035,
            "min_months": 6,
            "max_months": 120,
            "min_amount": 1000,
            "liquidity": "media",
        },
        {
            "id": "PROD003",
            "name": "Fondo Equilibrado B",
            "type": "moderado",
            "annual_rate": 0.065,
            "min_months": 12,
            "max_months": 120,
            "min_amount": 2000,
            "liquidity": "media",
        },
        {
            "id": "PROD005",
            "name": "Fondo Crecimiento C",
            "type": "agresivo",
            "annual_rate": 0.095,
            "min_months": 36,
            "max_months": 120,
            "min_amount": 5000,
            "liquidity": "baja",
        },
    ]


@pytest.fixture
def sample_client_profile():
    """Fixture for sample client profile"""
    return {
        "client_id": "TEST_CLI_001",
        "name": "Test Client",
        "risk_profile": "moderado",
        "investment_horizon_months": 24,
        "available_amount_usd": 50000,
        "liquidity_preference": "media",
        "target_return_pct": 8.0,
        "max_aggressive_pct": 40,
    }


@pytest.fixture
def sample_portfolio_allocation():
    """Fixture for sample portfolio allocation"""
    return [
        {
            "product_id": "PROD001",
            "product_name": "Fondo Conservador A",
            "percentage": 40,
            "amount": 20000,
            "annual_rate": 0.035,
        },
        {
            "product_id": "PROD003",
            "product_name": "Fondo Equilibrado B",
            "percentage": 40,
            "amount": 20000,
            "annual_rate": 0.065,
        },
        {
            "product_id": "PROD005",
            "product_name": "Fondo Crecimiento C",
            "percentage": 20,
            "amount": 10000,
            "annual_rate": 0.095,
        },
    ]


@pytest.fixture
def market_api_server():
    """Fixture for Market API server"""
    return MarketAPIServer()


# Configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (requiring external services)"
    )
    config.addinivalue_line(
        "markers",
        "unit: marks tests as unit tests (no external dependencies)"
    )
    config.addinivalue_line(
        "markers",
        "e2e: marks tests as end-to-end tests"
    )
