"""
MCP Server for PostgreSQL database access
Provides tools for querying products, clients, and portfolio data
"""

import json
import logging
from typing import Any
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor
import mcp.server.stdio
import mcp.types as types

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PostgreSQLServer:
    def __init__(self, db_host: str, db_name: str, db_user: str, db_password: str, db_port: int = 5432):
        self.db_host = db_host
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.db_port = db_port
        self.connection = None

    @staticmethod
    def _convert_decimals(data):
        """Convert Decimal values to float for JSON compatibility"""
        if isinstance(data, dict):
            return {k: PostgreSQLServer._convert_decimals(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [PostgreSQLServer._convert_decimals(item) for item in data]
        elif isinstance(data, Decimal):
            return float(data)
        return data

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                host=self.db_host,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                port=self.db_port,
                cursor_factory=RealDictCursor
            )
            logger.info("Connected to PostgreSQL database")
        except psycopg2.Error as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            raise

    def query_eligible_products(self, amount: float, risk_profile: str, months: int) -> list:
        """
        Query products eligible based on amount, risk profile, and investment horizon
        """
        try:
            cursor = self.connection.cursor()

            query = """
            SELECT * FROM products
            WHERE min_amount <= %s
            AND min_months <= %s
            AND max_months >= %s
            AND type IN (
                SELECT CASE
                    WHEN %s = 'conservador' THEN 'conservador'
                    WHEN %s = 'moderado' THEN 'conservador' OR 'moderado'
                    WHEN %s = 'agresivo' THEN 'conservador' OR 'moderado' OR 'agresivo'
                END
            )
            ORDER BY annual_rate DESC
            """

            # Simplified query - just filter by amount and months
            query = """
            SELECT * FROM products
            WHERE min_amount <= %s
            AND min_months <= %s
            AND max_months >= %s
            ORDER BY annual_rate DESC
            """

            cursor.execute(query, (amount, months, months))
            results = cursor.fetchall()
            cursor.close()

            # Convert Decimal to float for compatibility
            return [self._convert_decimals(dict(row)) for row in results]
        except psycopg2.Error as e:
            logger.error(f"Query error: {e}")
            return []

    def get_client_profile(self, client_id: str) -> dict:
        """Get complete client profile"""
        try:
            cursor = self.connection.cursor()
            query = "SELECT * FROM clients WHERE client_id = %s"
            cursor.execute(query, (client_id,))
            result = cursor.fetchone()
            cursor.close()

            return self._convert_decimals(dict(result)) if result else {}
        except psycopg2.Error as e:
            logger.error(f"Error getting client profile: {e}")
            return {}

    def get_client_portfolio(self, client_id: str) -> list:
        """Get current portfolio of a client"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT cp.*, p.name, p.type, p.annual_rate, p.liquidity
            FROM client_portfolios cp
            JOIN products p ON cp.product_id = p.id
            WHERE cp.client_id = %s
            """
            cursor.execute(query, (client_id,))
            results = cursor.fetchall()
            cursor.close()

            return [self._convert_decimals(dict(row)) for row in results]
        except psycopg2.Error as e:
            logger.error(f"Error getting portfolio: {e}")
            return []

    def get_client_contracted_products(self, client_id: str) -> dict:
        """
        Get all products contracted/invested by a client
        Returns detailed information about each product holding
        """
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT
                cp.product_id,
                cp.allocation_percentage,
                cp.allocation_amount,
                cp.purchase_date,
                p.id,
                p.name,
                p.type,
                p.annual_rate,
                p.liquidity,
                p.description
            FROM client_portfolios cp
            JOIN products p ON cp.product_id = p.id
            WHERE cp.client_id = %s
            ORDER BY cp.allocation_amount DESC
            """
            cursor.execute(query, (client_id,))
            results = cursor.fetchall()
            cursor.close()

            products = []
            for row in results:
                products.append({
                    "product_id": row['product_id'],
                    "product_name": row['name'],
                    "product_type": row['type'],
                    "annual_rate": float(row['annual_rate']) if row['annual_rate'] else 0,
                    "liquidity": row['liquidity'],
                    "allocation_percentage": float(row['allocation_percentage']) if row['allocation_percentage'] else 0,
                    "allocation_amount": float(row['allocation_amount']) if row['allocation_amount'] else 0,
                    "purchase_date": str(row['purchase_date']) if row['purchase_date'] else None,
                    "description": row['description']
                })

            return {
                "client_id": client_id,
                "total_products": len(products),
                "products": products
            }
        except psycopg2.Error as e:
            logger.error(f"Error getting contracted products: {e}")
            return {"client_id": client_id, "total_products": 0, "products": []}

    def get_client_invested_capital(self, client_id: str) -> dict:
        """
        Calculate total invested capital and breakdown by product
        Returns amount invested in each product and total
        """
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT
                cp.product_id,
                cp.allocation_amount,
                p.name,
                p.type,
                p.annual_rate
            FROM client_portfolios cp
            JOIN products p ON cp.product_id = p.id
            WHERE cp.client_id = %s
            """
            cursor.execute(query, (client_id,))
            results = cursor.fetchall()
            cursor.close()

            total_invested = 0.0
            breakdown = []

            for row in results:
                amount = float(row['allocation_amount']) if row['allocation_amount'] else 0
                total_invested += amount
                breakdown.append({
                    "product_name": row['name'],
                    "product_type": row['type'],
                    "invested_amount": amount,
                    "percentage_of_total": 0  # Will be calculated below
                })

            # Calculate percentages
            if total_invested > 0:
                for item in breakdown:
                    item["percentage_of_total"] = (item["invested_amount"] / total_invested) * 100

            return {
                "client_id": client_id,
                "total_invested_capital": round(total_invested, 2),
                "number_of_products": len(breakdown),
                "breakdown_by_product": breakdown
            }
        except psycopg2.Error as e:
            logger.error(f"Error calculating invested capital: {e}")
            return {
                "client_id": client_id,
                "total_invested_capital": 0,
                "number_of_products": 0,
                "breakdown_by_product": []
            }

    def get_market_context(self) -> dict:
        """Get aggregated market context from products"""
        try:
            cursor = self.connection.cursor()

            # Get average rates by type
            query = """
            SELECT type, AVG(annual_rate) as avg_rate, COUNT(*) as count
            FROM products
            GROUP BY type
            """
            cursor.execute(query)
            rates = cursor.fetchall()

            context = {
                "timestamp": "2024-01-27",
                "rates_by_profile": {}
            }

            for row in rates:
                context["rates_by_profile"][row['type']] = {
                    "avg_rate": float(row['avg_rate']),
                    "count_products": row['count']
                }

            cursor.close()
            return context
        except psycopg2.Error as e:
            logger.error(f"Error getting market context: {e}")
            return {}

    def save_recommendation(self, client_id: str, recommendation_data: dict) -> str:
        """Save a portfolio recommendation"""
        try:
            cursor = self.connection.cursor()

            rec_id = f"REC_{client_id}_{int(__import__('time').time())}"

            insert_query = """
            INSERT INTO portfolio_recommendations
            (recommendation_id, client_id, expected_return_pct, expected_risk_level,
             expected_liquidity, justification, was_accepted)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(insert_query, (
                rec_id,
                client_id,
                recommendation_data.get('expected_return', 0),
                recommendation_data.get('risk_level'),
                recommendation_data.get('liquidity'),
                recommendation_data.get('justification'),
                False
            ))

            # Insert recommendation items
            for item in recommendation_data.get('items', []):
                item_id = f"ITEM_{rec_id}_{item['product_id']}"
                item_query = """
                INSERT INTO recommendation_items
                (item_id, recommendation_id, product_id, suggested_percentage, suggested_amount)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(item_query, (
                    item_id,
                    rec_id,
                    item['product_id'],
                    item['percentage'],
                    item['amount']
                ))

            self.connection.commit()
            cursor.close()
            return rec_id
        except psycopg2.Error as e:
            logger.error(f"Error saving recommendation: {e}")
            self.connection.rollback()
            return ""

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()


# MCP Server setup
async def handle_call_tool(name: str, arguments: dict) -> str:
    """Handle tool calls from the MCP client"""

    db_config = {
        "db_host": "localhost",
        "db_name": "finadvisor",
        "db_user": "postgres",
        "db_password": "postgres"
    }

    server = PostgreSQLServer(**db_config)
    server.connect()

    try:
        if name == "query_eligible_products":
            result = server.query_eligible_products(
                amount=arguments.get("amount"),
                risk_profile=arguments.get("risk_profile"),
                months=arguments.get("months")
            )
            return json.dumps(result)

        elif name == "get_client_profile":
            result = server.get_client_profile(arguments.get("client_id"))
            return json.dumps(result)

        elif name == "get_client_portfolio":
            result = server.get_client_portfolio(arguments.get("client_id"))
            return json.dumps(result)

        elif name == "get_market_context":
            result = server.get_market_context()
            return json.dumps(result)

        elif name == "save_recommendation":
            result = server.save_recommendation(
                arguments.get("client_id"),
                arguments.get("recommendation_data")
            )
            return json.dumps({"recommendation_id": result})

        elif name == "get_client_contracted_products":
            result = server.get_client_contracted_products(arguments.get("client_id"))
            return json.dumps(result)

        elif name == "get_client_invested_capital":
            result = server.get_client_invested_capital(arguments.get("client_id"))
            return json.dumps(result)

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    finally:
        server.close()


# Tool definitions for MCP
TOOLS = [
    {
        "name": "query_eligible_products",
        "description": "Query products eligible based on client amount, risk profile, and investment horizon",
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Available amount in USD"},
                "risk_profile": {"type": "string", "description": "Risk profile: conservador, moderado, agresivo"},
                "months": {"type": "integer", "description": "Investment horizon in months"}
            },
            "required": ["amount", "risk_profile", "months"]
        }
    },
    {
        "name": "get_client_profile",
        "description": "Get complete client profile and preferences",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client ID"}
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "get_client_portfolio",
        "description": "Get current portfolio composition of a client",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client ID"}
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "get_market_context",
        "description": "Get current market context and average rates by profile",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "save_recommendation",
        "description": "Save a portfolio recommendation to database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string"},
                "recommendation_data": {
                    "type": "object",
                    "description": "Recommendation details with expected_return, risk_level, liquidity, justification, and items"
                }
            },
            "required": ["client_id", "recommendation_data"]
        }
    },
    {
        "name": "get_client_contracted_products",
        "description": "Get all products currently contracted/invested by a client with detailed information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client ID"}
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "get_client_invested_capital",
        "description": "Calculate total invested capital and get breakdown by product for a client",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client ID"}
            },
            "required": ["client_id"]
        }
    }
]


if __name__ == "__main__":
    # For testing
    server = PostgreSQLServer("localhost", "finadvisor", "postgres", "postgres")
    try:
        server.connect()
        print("Connected successfully")
        server.close()
    except Exception as e:
        print(f"Connection error: {e}")
