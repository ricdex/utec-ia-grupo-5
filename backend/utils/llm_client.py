"""
LLM Client abstraction layer
Supports multiple LLM providers: Anthropic, AWS Bedrock, and Local Ollama
"""

import logging
import os
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Get timeout from environment variable (default 30 seconds)
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def create_message(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None
    ) -> Any:
        """Create a message and get response from LLM"""
        pass


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude API provider"""

    def __init__(self, api_key: Optional[str] = None):
        from anthropic import Anthropic

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key)
        logger.info("Initialized Anthropic LLM provider")

    def create_message(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None
    ) -> Any:
        """Create message with Anthropic API"""

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages
        }

        if tools:
            kwargs["tools"] = tools

        return self.client.messages.create(**kwargs)


class BedrockLLMProvider(LLMProvider):
    """AWS Bedrock provider for Claude models"""

    def __init__(self, region: Optional[str] = None):
        import boto3

        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.client = boto3.client("bedrock-runtime", region_name=self.region)
        logger.info(f"Initialized Bedrock LLM provider (region: {self.region})")

    def create_message(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None
    ) -> Any:
        """Create message with Bedrock API"""
        import json

        # Bedrock expects a different message format
        body = {
            "anthropic_version": "bedrock-2023-06-01",
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages
        }

        if tools:
            body["tools"] = tools

        response = self.client.invoke_model(
            modelId=model,
            body=json.dumps(body)
        )

        # Parse response
        result = json.loads(response["body"].read())

        # Wrap in Anthropic-like response object for compatibility
        class BedrockResponse:
            def __init__(self, data):
                self.content = data.get("content", [])
                self.stop_reason = data.get("stop_reason", "end_turn")

        return BedrockResponse(result)


class OllamaLLMProvider(LLMProvider):
    """Local Ollama provider for running models locally"""

    def __init__(self, base_url: Optional[str] = None):
        import requests

        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.requests = requests
        logger.info(f"Initialized Ollama LLM provider (base_url: {self.base_url})")

    def _check_model_availability(self, model: str) -> bool:
        """Check if model is available in Ollama"""
        try:
            response = self.requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                return model.split(":")[0] in model_names
        except Exception as e:
            logger.warning(f"Could not check Ollama models: {e}")
        return False

    def create_message(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None
    ) -> Any:
        """Create message with Ollama API"""

        # Check if model is available
        if not self._check_model_availability(model):
            logger.warning(f"Model {model} not available in Ollama. Available models can be checked with: ollama list")

        # Convert messages to Ollama format
        ollama_messages = []

        # Add system message as first user message if needed
        for msg in messages:
            ollama_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        try:
            response = self.requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": ollama_messages,
                    "system": system,
                    "stream": False
                },
                timeout=API_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()

                # Wrap in Anthropic-like response for compatibility
                class OllamaResponse:
                    def __init__(self, data):
                        # Extract text content
                        text_content = data.get("message", {}).get("content", "")
                        self.content = [{"type": "text", "text": text_content}]
                        self.stop_reason = "end_turn"

                return OllamaResponse(result)
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                raise Exception(f"Ollama API returned {response.status_code}")

        except Exception as e:
            logger.error(f"Ollama request error: {e}")
            raise


class LLMClientFactory:
    """Factory for creating LLM clients based on configuration"""

    _providers = {
        "anthropic": AnthropicLLMProvider,
        "bedrock": BedrockLLMProvider,
        "local": OllamaLLMProvider
    }

    @staticmethod
    def create_client(provider: str = "anthropic", **kwargs) -> LLMProvider:
        """
        Create an LLM client based on provider type

        Args:
            provider: 'anthropic', 'bedrock', or 'local'
            **kwargs: Provider-specific arguments

        Returns:
            LLMProvider instance
        """

        if provider not in LLMClientFactory._providers:
            raise ValueError(f"Unknown provider: {provider}. Supported: {list(LLMClientFactory._providers.keys())}")

        provider_class = LLMClientFactory._providers[provider]
        return provider_class(**kwargs)

    @staticmethod
    def create_from_config(config) -> LLMProvider:
        """
        Create an LLM client from a Config object

        Args:
            config: Config instance

        Returns:
            LLMProvider instance
        """

        provider = config.get_model_provider()

        if provider == "local":
            return LLMClientFactory.create_client(
                "local",
                base_url=config.get_ollama_base_url()
            )
        elif provider == "bedrock":
            return LLMClientFactory.create_client(
                "bedrock",
                region=os.getenv("AWS_REGION")
            )
        else:  # anthropic
            return LLMClientFactory.create_client(
                "anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )


__all__ = [
    "LLMProvider",
    "AnthropicLLMProvider",
    "BedrockLLMProvider",
    "OllamaLLMProvider",
    "LLMClientFactory"
]
