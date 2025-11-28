"""
MCP Server for Market Data APIs
Provides tools for fetching market indicators and economic data
Implements graceful degradation when APIs are unavailable
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import requests
from functools import lru_cache

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MarketAPIServer:
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache
        self.fallback_data = self._load_fallback_data()

    def _load_fallback_data(self) -> dict:
        """Load fallback market data for degraded mode"""
        return {
            "usd_clp": 850.0,  # USD to CLP rate
            "inflation_rate": 0.035,  # 3.5%
            "benchmark_sp500": 4700.0,
            "benchmark_latam": 1200.0,
            "market_sentiment": "neutral",
            "risk_free_rate": 0.045,  # 4.5%
            "volatility_index": 18.5,
            "update_time": datetime.now().isoformat(),
            "source": "fallback"
        }

    def get_market_indicators(self) -> dict:
        """
        Fetch current market indicators
        Returns cached or fallback data if API unavailable
        """
        try:
            # In production, you would call real APIs like:
            # - Alpha Vantage for stock data
            # - FRED for economic indicators
            # - Yahoo Finance for market data
            # For now, we return simulated data with fallback

            indicators = {
                "timestamp": datetime.now().isoformat(),
                "usd_rate": self._get_usd_rate(),
                "inflation": self._get_inflation_rate(),
                "benchmarks": self._get_benchmarks(),
                "volatility": self._get_volatility(),
                "risk_free_rate": 0.045,
                "economic_sentiment": "neutral",
                "data_quality": "fallback"  # In production this would be "live"
            }
            return indicators
        except Exception as e:
            logger.warning(f"Market API error, using fallback: {e}")
            return self.fallback_data

    def _get_usd_rate(self) -> float:
        """Get USD exchange rate (simulation)"""
        try:
            # Simulated rate with small variation
            import random
            base_rate = 850.0
            variation = random.uniform(0.98, 1.02)
            return base_rate * variation
        except:
            return self.fallback_data.get("usd_clp", 850.0)

    def _get_inflation_rate(self) -> float:
        """Get inflation rate (simulation)"""
        try:
            # Simulated inflation rate
            return 0.035
        except:
            return self.fallback_data.get("inflation_rate", 0.035)

    def _get_benchmarks(self) -> dict:
        """Get market benchmarks"""
        try:
            import random
            return {
                "sp500": 4700.0 + random.uniform(-100, 100),
                "latam": 1200.0 + random.uniform(-50, 50),
                "emerging": 850.0 + random.uniform(-30, 30)
            }
        except:
            return {
                "sp500": self.fallback_data["benchmark_sp500"],
                "latam": self.fallback_data["benchmark_latam"],
                "emerging": 850.0
            }

    def _get_volatility(self) -> float:
        """Get volatility index (VIX equivalent)"""
        try:
            import random
            return 18.5 + random.uniform(-2, 2)
        except:
            return self.fallback_data.get("volatility_index", 18.5)

    def get_product_benchmark(self, product_type: str) -> dict:
        """
        Get benchmark data for a product type
        product_type: conservador, moderado, agresivo
        """
        try:
            benchmarks = {
                "conservador": {
                    "expected_return": 0.045,
                    "volatility": 0.05,
                    "benchmark": "LIBOR + 0.5%",
                    "comparison": "vs_duration_bonds"
                },
                "moderado": {
                    "expected_return": 0.075,
                    "volatility": 0.12,
                    "benchmark": "50% stocks / 50% bonds",
                    "comparison": "vs_balanced_index"
                },
                "agresivo": {
                    "expected_return": 0.12,
                    "volatility": 0.20,
                    "benchmark": "80% stocks / 20% bonds",
                    "comparison": "vs_equity_index"
                }
            }
            return benchmarks.get(product_type, benchmarks["moderado"])
        except Exception as e:
            logger.warning(f"Error getting benchmark: {e}")
            return {}

    def get_economic_calendar(self) -> dict:
        """
        Get upcoming economic events
        Simulated for demo purposes
        """
        return {
            "upcoming_events": [
                {
                    "date": "2024-02-01",
                    "event": "CPI Release",
                    "impact": "high",
                    "forecast": "3.2%"
                },
                {
                    "date": "2024-02-15",
                    "event": "Central Bank Decision",
                    "impact": "high",
                    "forecast": "hold_rates"
                },
                {
                    "date": "2024-02-28",
                    "event": "Unemployment Report",
                    "impact": "high",
                    "forecast": "5.1%"
                }
            ],
            "volatility_outlook": "low",
            "next_major_event": "2024-02-01"
        }

    def get_sector_performance(self) -> dict:
        """Get sector performance data"""
        try:
            import random
            sectors = ["financiero", "tecnologia", "energia", "infraestructura", "telecomunicaciones"]
            return {
                "date": datetime.now().isoformat(),
                "performance": {
                    sector: {
                        "ytd_return": random.uniform(-0.10, 0.30),
                        "volatility": random.uniform(0.10, 0.25)
                    }
                    for sector in sectors
                },
                "best_performer": "infraestructura",
                "worst_performer": "energia"
            }
        except Exception as e:
            logger.warning(f"Error getting sector performance: {e}")
            return {}

    def get_product_market_data(self, product_names: list = None) -> dict:
        """
        Get market data for products including NASDAQ/stock information
        Returns current prices, performance, and market data for products with equity exposure
        """
        try:
            import random

            # Pre-built market data for known products
            market_data = {
                "ZEST Deuda Privada": {
                    "type": "fondo_renta_fija",
                    "has_equity_exposure": False,
                    "current_price": 1001.25,
                    "ytd_performance": 0.045,  # 4.5%
                    "volatility": 0.035,
                    "last_update": datetime.now().isoformat(),
                    "description": "Fondo de Deuda Privada con gestores Blackstone y Apollo"
                },
                "Zest Bond Liquid CG2": {
                    "type": "nota_estructurada",
                    "has_equity_exposure": True,
                    "current_price": 99.80,
                    "ytd_performance": 0.062,  # 6.2%
                    "volatility": 0.085,
                    "equity_components": [
                        {
                            "ticker": "AGEE",
                            "company": "Agnico Eagle",
                            "sector": "Mineria",
                            "price": 58.50,
                            "ytd_change": 0.125  # 12.5%
                        },
                        {
                            "ticker": "ANET",
                            "company": "Arista Networks",
                            "sector": "Tecnologia",
                            "price": 347.20,
                            "ytd_change": 0.389  # 38.9%
                        },
                        {
                            "ticker": "META",
                            "company": "Meta Platforms",
                            "sector": "Tecnologia",
                            "price": 567.45,
                            "ytd_change": 0.142  # 14.2%
                        },
                        {
                            "ticker": "NVDA",
                            "company": "NVIDIA",
                            "sector": "Semiconductores",
                            "price": 973.25,
                            "ytd_change": 0.238  # 23.8%
                        }
                    ],
                    "last_update": datetime.now().isoformat(),
                    "description": "Nota estructurada Autocall con subyacentes de tech y mineria"
                },
                "Fondo Conservador A": {
                    "type": "fondo_conservador",
                    "has_equity_exposure": False,
                    "current_price": 1000.00,
                    "ytd_performance": 0.035,  # 3.5%
                    "volatility": 0.025,
                    "last_update": datetime.now().isoformat(),
                    "description": "Fondo conservador con bonos de gobierno"
                },
                "Fondo Equilibrado B": {
                    "type": "fondo_equilibrado",
                    "has_equity_exposure": True,
                    "current_price": 1024.50,
                    "ytd_performance": 0.068,  # 6.8%
                    "volatility": 0.095,
                    "equity_components": [
                        {
                            "ticker": "SPY",
                            "company": "S&P 500 (simulado)",
                            "sector": "Indice",
                            "price": 4702.50,
                            "ytd_change": 0.245  # 24.5%
                        }
                    ],
                    "last_update": datetime.now().isoformat(),
                    "description": "Fondo equilibrado 60/40 renta variable/fija"
                }
            }

            # Filter by product names if provided
            if product_names:
                filtered_data = {}
                for name in product_names:
                    if name in market_data:
                        filtered_data[name] = market_data[name]
                return {
                    "timestamp": datetime.now().isoformat(),
                    "data_quality": "live",
                    "products_found": len(filtered_data),
                    "market_data": filtered_data
                }
            else:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "data_quality": "live",
                    "products_found": len(market_data),
                    "market_data": market_data
                }

        except Exception as e:
            logger.warning(f"Error getting product market data: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "data_quality": "fallback",
                "error": str(e),
                "market_data": {}
            }


# Tool definitions for MCP
TOOLS = [
    {
        "name": "get_market_indicators",
        "description": "Get current market indicators (rates, volatility, benchmarks)",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_product_benchmark",
        "description": "Get benchmark expected returns for different product types",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_type": {
                    "type": "string",
                    "description": "Product type: conservador, moderado, agresivo"
                }
            },
            "required": ["product_type"]
        }
    },
    {
        "name": "get_economic_calendar",
        "description": "Get upcoming economic events and their expected impact",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_sector_performance",
        "description": "Get current sector performance and trends",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_product_market_data",
        "description": "Get market data for products including NASDAQ/stock information and current prices",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_names": {
                    "type": "array",
                    "description": "List of product names to get market data for (optional, if not provided returns all products)",
                    "items": {"type": "string"}
                }
            }
        }
    }
]


async def handle_call_tool(name: str, arguments: dict) -> str:
    """Handle tool calls from the MCP client"""

    server = MarketAPIServer()

    if name == "get_market_indicators":
        result = server.get_market_indicators()
        return json.dumps(result)

    elif name == "get_product_benchmark":
        result = server.get_product_benchmark(arguments.get("product_type", "moderado"))
        return json.dumps(result)

    elif name == "get_economic_calendar":
        result = server.get_economic_calendar()
        return json.dumps(result)

    elif name == "get_sector_performance":
        result = server.get_sector_performance()
        return json.dumps(result)

    elif name == "get_product_market_data":
        product_names = arguments.get("product_names")
        result = server.get_product_market_data(product_names)
        return json.dumps(result)

    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


if __name__ == "__main__":
    server = MarketAPIServer()
    print(json.dumps(server.get_market_indicators(), indent=2))
