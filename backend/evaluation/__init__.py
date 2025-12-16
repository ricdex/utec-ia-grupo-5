"""
LangSmith Evaluation Module for FinAdvisor
Implements 6 key metrics for evaluating the agent's performance
"""

from .evaluators import (
    hard_goals_compliance,
    no_guarantees_and_has_disclaimer,
    clarification_trigger,
    grounded_recommendation,
    explainability_score,
    sequential_orchestration_correctness
)

# Optional LLM-as-judge evaluator
try:
    from .llm_judge import get_llm_judge
    _llm_judge_available = True
except ImportError:
    _llm_judge_available = False
    get_llm_judge = None

__all__ = [
    "hard_goals_compliance",
    "no_guarantees_and_has_disclaimer",
    "clarification_trigger",
    "grounded_recommendation",
    "explainability_score",
    "sequential_orchestration_correctness",
    "get_llm_judge"
]
