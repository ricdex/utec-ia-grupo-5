"""
FinAdvisor Orchestrator Package

This package contains the orchestration layer for FinAdvisor:
- core.py: Shared business logic (FinAdvisorOrchestrator class)
- cloud.py: AWS Lambda entry point (cloud-specific)
- local.py: FastAPI server (local development-specific)
"""

__all__ = ["FinAdvisorOrchestrator"]

from orchestrator.core import FinAdvisorOrchestrator
