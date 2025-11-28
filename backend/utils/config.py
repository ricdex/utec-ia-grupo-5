"""
Configuration management for FinAdvisor
Handles loading configuration from config.json and environment variables
"""

import json
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for FinAdvisor"""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration from JSON file and environment variables
        Environment variables override JSON config
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file {self.config_path} not found, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "model": {
                "provider": "anthropic",
                "name": "claude-3-5-sonnet-20241022",
                "ollama_base_url": "http://localhost:11434"
            },
            "database": {
                "host": "localhost",
                "name": "finadvisor",
                "user": "postgres",
                "password": "postgres",
                "port": 5432
            },
            "api": {
                "port": 8000,
                "host": "0.0.0.0"
            }
        }

    # Model Configuration
    def get_model_provider(self) -> str:
        """Get the model provider (anthropic, bedrock, or local)"""
        return os.getenv("MODEL_PROVIDER", self.config.get("model", {}).get("provider", "anthropic"))

    def get_model_name(self) -> str:
        """Get the model name/ID"""
        return os.getenv("MODEL_NAME", self.config.get("model", {}).get("name", "claude-3-5-sonnet-20241022"))

    def get_ollama_base_url(self) -> str:
        """Get Ollama base URL for local development"""
        return os.getenv("OLLAMA_BASE_URL", self.config.get("model", {}).get("ollama_base_url", "http://localhost:11434"))

    def get_available_models(self, provider: Optional[str] = None) -> List[Dict]:
        """
        Get list of available models
        provider: 'anthropic' or 'bedrock' (default: uses current provider)
        """
        if provider is None:
            provider = self.get_model_provider()

        available = self.config.get("model", {}).get("available_models", {})
        return available.get(provider, [])

    def get_model_info(self, model_id: str, provider: Optional[str] = None) -> Optional[Dict]:
        """Get information about a specific model"""
        if provider is None:
            provider = self.get_model_provider()

        models = self.get_available_models(provider)
        for model in models:
            if model.get("id") == model_id:
                return model
        return None

    # Database Configuration
    def get_db_host(self) -> str:
        """Get database host"""
        return os.getenv("DB_HOST", self.config.get("database", {}).get("host", "localhost"))

    def get_db_name(self) -> str:
        """Get database name"""
        return os.getenv("DB_NAME", self.config.get("database", {}).get("name", "finadvisor"))

    def get_db_user(self) -> str:
        """Get database user"""
        return os.getenv("DB_USER", self.config.get("database", {}).get("user", "postgres"))

    def get_db_password(self) -> str:
        """Get database password"""
        return os.getenv("DB_PASSWORD", self.config.get("database", {}).get("password", "postgres"))

    def get_db_port(self) -> int:
        """Get database port"""
        return int(os.getenv("DB_PORT", self.config.get("database", {}).get("port", 5432)))

    def get_db_config(self) -> Dict:
        """Get complete database configuration"""
        return {
            "db_host": self.get_db_host(),
            "db_name": self.get_db_name(),
            "db_user": self.get_db_user(),
            "db_password": self.get_db_password(),
            "db_port": self.get_db_port()
        }

    # API Configuration
    def get_api_port(self) -> int:
        """Get API port"""
        return int(os.getenv("API_PORT", self.config.get("api", {}).get("port", 8000)))

    def get_api_host(self) -> str:
        """Get API host"""
        return os.getenv("API_HOST", self.config.get("api", {}).get("host", "0.0.0.0"))

    def get_api_debug(self) -> bool:
        """Get debug mode"""
        return os.getenv("API_DEBUG", "false").lower() == "true"

    # RAG Configuration
    def is_rag_enabled(self) -> bool:
        """Check if RAG is enabled"""
        return os.getenv("RAG_ENABLED", str(self.config.get("rag", {}).get("enabled", True))).lower() == "true"

    def get_rag_embedding_dimension(self) -> int:
        """Get RAG embedding dimension"""
        return int(os.getenv("RAG_EMBEDDING_DIM", self.config.get("rag", {}).get("embedding_dimension", 384)))

    def get_rag_similarity_threshold(self) -> float:
        """Get RAG similarity threshold"""
        return float(os.getenv("RAG_SIMILARITY_THRESHOLD", self.config.get("rag", {}).get("similarity_threshold", 0.3)))

    # Logging Configuration
    def get_log_level(self) -> str:
        """Get logging level"""
        return os.getenv("LOG_LEVEL", self.config.get("logging", {}).get("level", "INFO"))

    # Utility methods
    def update_model(self, provider: str, model_name: str):
        """Update model configuration at runtime"""
        self.config["model"]["provider"] = provider
        self.config["model"]["name"] = model_name
        logger.info(f"Model updated: {provider}/{model_name}")

    def to_dict(self) -> Dict:
        """Convert config to dictionary (excluding sensitive info)"""
        return {
            "model": {
                "provider": self.get_model_provider(),
                "name": self.get_model_name()
            },
            "database": {
                "host": self.get_db_host(),
                "port": self.get_db_port()
            },
            "api": {
                "host": self.get_api_host(),
                "port": self.get_api_port()
            },
            "rag_enabled": self.is_rag_enabled()
        }


# Global config instance
_config_instance = None


def get_config() -> Config:
    """Get global config instance (singleton pattern)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# Export
__all__ = ["Config", "get_config"]
