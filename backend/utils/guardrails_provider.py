"""
Guardrails Provider abstraction layer
Supports multiple guardrails providers: Local (guardrails.py) and AWS Bedrock Guardrails
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from utils.guardrails import GuardrailViolation, FinancialGuardrails

logger = logging.getLogger(__name__)


class GuardrailsProvider(ABC):
    """Abstract base class for guardrails providers"""

    @abstractmethod
    def validate_recommendation(
        self,
        client_profile: Dict,
        portfolio_allocation: List[Dict],
        expected_return: float
    ) -> Tuple[bool, List[GuardrailViolation]]:
        """Validate portfolio recommendation against guardrails"""
        pass

    @abstractmethod
    def needs_human_escalation(self, violations: List[GuardrailViolation]) -> bool:
        """Check if violations require human escalation"""
        pass

    @abstractmethod
    def generate_disclaimer(self) -> str:
        """Generate mandatory disclaimer text"""
        pass

    @abstractmethod
    def validate_data_sufficiency(self, client_profile: Dict) -> Tuple[bool, str]:
        """Validate if client data is sufficient for recommendation"""
        pass


class LocalGuardrailsProvider(GuardrailsProvider):
    """Local guardrails provider using guardrails.py"""

    def __init__(self):
        logger.info("Initialized Local Guardrails provider")

    def validate_recommendation(self, client_profile, portfolio_allocation, expected_return):
        return FinancialGuardrails.validate_recommendation(
            client_profile, portfolio_allocation, expected_return
        )

    def needs_human_escalation(self, violations):
        return FinancialGuardrails.needs_human_escalation(violations)

    def generate_disclaimer(self):
        return FinancialGuardrails.generate_disclaimer()

    def validate_data_sufficiency(self, client_profile):
        return FinancialGuardrails.validate_data_sufficiency(client_profile)


class BedrockGuardrailsProvider(GuardrailsProvider):
    """AWS Bedrock Guardrails provider with Automated Reasoning"""

    def __init__(self, guardrail_id: str, version: str = "DRAFT", region: str = "us-east-1"):
        import boto3

        self.guardrail_id = guardrail_id
        self.guardrail_version = version
        self.region = region
        self.client = boto3.client('bedrock-runtime', region_name=region)

        logger.info(f"Initialized Bedrock Guardrails (ID: {guardrail_id}, Version: {version}, Region: {region})")

    def validate_recommendation(self, client_profile, portfolio_allocation, expected_return):
        """Validate using Bedrock ApplyGuardrail API with Automated Reasoning"""

        # Format input for Bedrock
        assessment_input = self._format_for_bedrock(
            client_profile, portfolio_allocation, expected_return
        )

        try:
            # Call Bedrock ApplyGuardrail API
            response = self.client.apply_guardrail(
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version,
                source="INPUT",
                content=[{
                    "text": {"text": json.dumps(assessment_input)}
                }]
            )

            # Parse Bedrock response to GuardrailViolation format
            return self._parse_bedrock_response(response)

        except Exception as e:
            logger.error(f"Bedrock guardrails validation failed: {e}")
            logger.warning("Falling back to local guardrails validation")
            # Fallback to local validation
            return FinancialGuardrails.validate_recommendation(
                client_profile, portfolio_allocation, expected_return
            )

    def _format_for_bedrock(self, client_profile, portfolio_allocation, expected_return):
        """Convert to Bedrock AR policy input format"""
        return {
            "client": client_profile,
            "portfolio": portfolio_allocation,
            "metrics": {"expected_return": expected_return}
        }

    def _parse_bedrock_response(self, response):
        """Convert Bedrock response to (bool, List[GuardrailViolation])"""
        violations = []

        # Parse AR check results
        if "assessments" in response:
            for assessment in response["assessments"]:
                if assessment.get("action") == "BLOCKED":
                    violations.append(GuardrailViolation(
                        severity="error",
                        rule=assessment.get("type", "unknown"),
                        message=assessment.get("message", "Validation failed"),
                        action="escalate" if "ESCALATE" in assessment.get("type", "") else "clarify"
                    ))

        # Check if any critical violations
        is_valid = not any(v.severity == "error" for v in violations)

        # Always add disclaimer
        violations.append(GuardrailViolation(
            severity="warning",
            rule="mandatory_disclaimer",
            message=self.generate_disclaimer(),
            action="proceed"
        ))

        return (is_valid, violations)

    def needs_human_escalation(self, violations):
        return any(v.action == "escalate" for v in violations)

    def generate_disclaimer(self):
        # Same disclaimer as local
        return FinancialGuardrails.generate_disclaimer()

    def validate_data_sufficiency(self, client_profile):
        # Pre-validate locally before calling Bedrock (faster)
        return FinancialGuardrails.validate_data_sufficiency(client_profile)


class GuardrailsProviderFactory:
    """Factory for creating guardrails providers"""

    _providers = {
        "local": LocalGuardrailsProvider,
        "bedrock": BedrockGuardrailsProvider
    }

    @staticmethod
    def create_from_config(config) -> GuardrailsProvider:
        """Create provider based on configuration"""

        provider_type = config.get_guardrails_provider()

        if provider_type == "bedrock":
            guardrail_id = config.get_bedrock_guardrail_id()
            if not guardrail_id:
                logger.warning("Bedrock provider selected but no guardrail ID configured. Falling back to local provider.")
                return LocalGuardrailsProvider()

            return BedrockGuardrailsProvider(
                guardrail_id=guardrail_id,
                version=config.get_bedrock_guardrail_version(),
                region=os.getenv("AWS_REGION", "us-east-1")
            )
        else:  # local (default)
            return LocalGuardrailsProvider()


__all__ = [
    "GuardrailsProvider",
    "LocalGuardrailsProvider",
    "BedrockGuardrailsProvider",
    "GuardrailsProviderFactory"
]
