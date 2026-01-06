"""
Memory management for the financial advisor agent
Implements STM (Short-Term Memory) with Redis and LTM (Long-Term Memory) with PostgreSQL
"""

import json
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisConversationBuffer:
    """
    Short-Term Memory using Redis
    Stores recent conversation context with TTL
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        max_messages: int = 30,
        ttl_seconds: int = 3600  # 1 hour default
    ):
        # Get Redis config from environment or use defaults
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", "6379"))
        self.max_messages = max_messages
        self.ttl_seconds = ttl_seconds

        # Connect to Redis
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _get_key(self, client_id: str) -> str:
        """Generate Redis key for client conversation"""
        return f"conversation:{client_id}"

    def add_message(self, client_id: str, role: str, content: str, metadata: Dict = None):
        """Add message to conversation buffer in Redis"""
        try:
            key = self._get_key(client_id)
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            # Add message to list
            self.redis_client.rpush(key, json.dumps(message))

            # Trim to keep only recent messages
            self.redis_client.ltrim(key, -self.max_messages, -1)

            # Set expiration
            self.redis_client.expire(key, self.ttl_seconds)

            logger.debug(f"Added {role} message to Redis for client {client_id}")
        except redis.RedisError as e:
            logger.error(f"Error adding message to Redis: {e}")
            raise

    def get_conversation_history(self, client_id: str, last_n: int = 10) -> List[Dict]:
        """Get recent conversation history from Redis"""
        try:
            key = self._get_key(client_id)
            messages = self.redis_client.lrange(key, -last_n, -1)
            return [json.loads(msg) for msg in messages]
        except redis.RedisError as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    def get_context(self, client_id: str) -> str:
        """Get formatted conversation context for LLM"""
        messages = self.get_conversation_history(client_id, last_n=5)
        context = "## Historial de Conversación Reciente:\n"
        for msg in messages:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            context += f"\n{role}: {msg['content']}"
        return context

    def clear(self, client_id: str):
        """Clear conversation history for a client"""
        try:
            key = self._get_key(client_id)
            self.redis_client.delete(key)
            logger.info(f"Cleared conversation for client {client_id}")
        except redis.RedisError as e:
            logger.error(f"Error clearing conversation: {e}")


class PostgreSQLClientProfile:
    """
    Long-Term Memory using PostgreSQL
    Stores client profiles, recommendations, and portfolio history
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None
    ):
        # Get PostgreSQL config from environment or use defaults
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = port or int(os.getenv("DB_PORT", "5432"))
        self.database = database or os.getenv("DB_NAME", "finadvisor")
        self.user = user or os.getenv("DB_USER", "postgres")
        self.password = password or os.getenv("DB_PASSWORD", "postgres")

        # Connect to PostgreSQL
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor
            )
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}/{self.database}")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    @staticmethod
    def _convert_to_json_serializable(data):
        """Convert Decimal and datetime values to JSON-serializable formats"""
        if isinstance(data, dict):
            return {k: PostgreSQLClientProfile._convert_to_json_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [PostgreSQLClientProfile._convert_to_json_serializable(item) for item in data]
        elif isinstance(data, Decimal):
            return float(data)
        elif isinstance(data, (datetime, date)):
            return data.isoformat()
        return data

    def get_profile(self, client_id: str) -> Dict:
        """Get client profile from PostgreSQL"""
        try:
            cursor = self.connection.cursor()
            query = "SELECT * FROM clients WHERE client_id = %s"
            cursor.execute(query, (client_id,))
            result = cursor.fetchone()
            cursor.close()

            if result:
                return self._convert_to_json_serializable(dict(result))
            else:
                # Return default profile if client doesn't exist
                return {
                    "client_id": client_id,
                    "risk_profile": None,
                    "investment_horizon_months": None,
                    "available_amount_usd": None,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
        except psycopg2.Error as e:
            logger.error(f"Error getting client profile: {e}")
            return {}

    def update_profile(self, client_id: str, **kwargs):
        """Update or insert client profile"""
        try:
            cursor = self.connection.cursor()

            # Check if client exists
            cursor.execute("SELECT client_id FROM clients WHERE client_id = %s", (client_id,))
            exists = cursor.fetchone()

            if exists:
                # Update existing profile
                set_clauses = []
                values = []
                for key, value in kwargs.items():
                    set_clauses.append(f"{key} = %s")
                    values.append(value)

                values.append(client_id)
                query = f"UPDATE clients SET {', '.join(set_clauses)}, updated_at = NOW() WHERE client_id = %s"
                cursor.execute(query, values)
            else:
                # Insert new profile
                columns = ["client_id"] + list(kwargs.keys())
                placeholders = ["%s"] * (len(kwargs) + 1)
                values = [client_id] + list(kwargs.values())

                query = f"""
                    INSERT INTO clients ({', '.join(columns)}, created_at, updated_at)
                    VALUES ({', '.join(placeholders)}, NOW(), NOW())
                """
                cursor.execute(query, values)

            self.connection.commit()
            cursor.close()
            logger.info(f"Updated profile for client {client_id}")
        except psycopg2.Error as e:
            logger.error(f"Error updating client profile: {e}")
            self.connection.rollback()

    def save_recommendation(self, client_id: str, recommendation: Dict):
        """Save portfolio recommendation to PostgreSQL"""
        try:
            cursor = self.connection.cursor()

            query = """
                INSERT INTO portfolio_recommendations (
                    client_id,
                    recommendation_date,
                    allocations,
                    expected_return,
                    expected_risk,
                    sharpe_ratio,
                    metadata
                )
                VALUES (%s, NOW(), %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                client_id,
                json.dumps(recommendation.get("allocations", [])),
                recommendation.get("expected_return"),
                recommendation.get("expected_risk"),
                recommendation.get("sharpe_ratio"),
                json.dumps(recommendation.get("metadata", {}))
            ))

            self.connection.commit()
            cursor.close()
            logger.info(f"Saved recommendation for client {client_id}")
        except psycopg2.Error as e:
            logger.error(f"Error saving recommendation: {e}")
            self.connection.rollback()

    def get_recommendations_history(self, client_id: str, limit: int = 10) -> List[Dict]:
        """Get recommendation history for a client"""
        try:
            cursor = self.connection.cursor()
            query = """
                SELECT * FROM portfolio_recommendations
                WHERE client_id = %s
                ORDER BY recommendation_date DESC
                LIMIT %s
            """
            cursor.execute(query, (client_id, limit))
            results = cursor.fetchall()
            cursor.close()

            return [self._convert_to_json_serializable(dict(row)) for row in results]
        except psycopg2.Error as e:
            logger.error(f"Error getting recommendations history: {e}")
            return []

    def get_portfolio(self, client_id: str) -> List[Dict]:
        """Get current portfolio holdings"""
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

            return [self._convert_to_json_serializable(dict(row)) for row in results]
        except psycopg2.Error as e:
            logger.error(f"Error getting portfolio: {e}")
            return []

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Closed PostgreSQL connection")


class MemoryManager:
    """
    Unified memory manager for STM (Redis) and LTM (PostgreSQL)
    Orchestrates both conversation and client profile memory
    """

    def __init__(self, client_id: str):
        self.client_id = client_id

        # Initialize STM with Redis
        try:
            self.stm = RedisConversationBuffer()
        except redis.ConnectionError as e:
            logger.warning(f"Redis not available, falling back to in-memory STM: {e}")
            # Fallback to in-memory buffer if Redis is not available
            self.stm = InMemoryConversationBuffer()

        # Initialize LTM with PostgreSQL
        try:
            self.ltm = PostgreSQLClientProfile()
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            raise

    def add_user_message(self, content: str, metadata: Dict = None):
        """Add user message to STM"""
        self.stm.add_message(self.client_id, "user", content, metadata)

    def add_assistant_message(self, content: str, metadata: Dict = None):
        """Add assistant message to STM"""
        self.stm.add_message(self.client_id, "assistant", content, metadata)

    def get_conversation_context(self) -> str:
        """Get context for LLM from STM"""
        return self.stm.get_context(self.client_id)

    def get_conversation_history(self, last_n: int = 10) -> List[Dict]:
        """Get conversation history"""
        return self.stm.get_conversation_history(self.client_id, last_n)

    def get_client_memory(self) -> Dict:
        """Get client profile for agent reasoning (LTM)"""
        return self.ltm.get_profile(self.client_id)

    def update_client_profile(self, **kwargs):
        """Update long-term client profile in PostgreSQL"""
        self.ltm.update_profile(self.client_id, **kwargs)

    def save_recommendation_to_ltm(self, recommendation: Dict):
        """Save recommendation to long-term memory in PostgreSQL"""
        self.ltm.save_recommendation(self.client_id, recommendation)

    def get_recommendations_history(self, limit: int = 10) -> List[Dict]:
        """Get recommendation history from LTM"""
        return self.ltm.get_recommendations_history(self.client_id, limit)

    def get_portfolio(self) -> List[Dict]:
        """Get current portfolio from LTM"""
        return self.ltm.get_portfolio(self.client_id)

    def clear_conversation(self):
        """Clear conversation history (STM)"""
        self.stm.clear(self.client_id)

    def close(self):
        """Close database connections"""
        self.ltm.close()


class InMemoryConversationBuffer:
    """
    Fallback in-memory conversation buffer
    Used when Redis is not available
    """

    def __init__(self, max_messages: int = 30):
        self.max_messages = max_messages
        self.conversations = {}  # client_id -> messages

    def add_message(self, client_id: str, role: str, content: str, metadata: Dict = None):
        """Add message to in-memory buffer"""
        if client_id not in self.conversations:
            self.conversations[client_id] = []

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.conversations[client_id].append(message)

        # Keep only recent messages
        if len(self.conversations[client_id]) > self.max_messages:
            self.conversations[client_id] = self.conversations[client_id][-self.max_messages:]

    def get_conversation_history(self, client_id: str, last_n: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        if client_id not in self.conversations:
            return []
        return self.conversations[client_id][-last_n:]

    def get_context(self, client_id: str) -> str:
        """Get formatted conversation context for LLM"""
        messages = self.get_conversation_history(client_id, last_n=5)
        context = "## Historial de Conversación Reciente:\n"
        for msg in messages:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            context += f"\n{role}: {msg['content']}"
        return context

    def clear(self, client_id: str):
        """Clear conversation history"""
        if client_id in self.conversations:
            del self.conversations[client_id]
