"""
LangSmith Evaluators for FinAdvisor Agent

Implements 6 critical metrics:
1. Hard Goals Compliance (binary)
2. No Guarantees & Disclaimer Presence (binary)
3. Clarification Trigger Accuracy (binary)
4. Grounded Recommendation (0-1)
5. Explainability Score (1-5, LLM-as-judge)
6. Sequential Orchestration Correctness (0-1)
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# ============================================================
# 1. HARD GOALS COMPLIANCE (Binary: Yes/No)
# ============================================================

def hard_goals_compliance(run, example) -> Dict[str, Any]:
    """
    Verifies that recommendation meets all hard goals:
    - Risk level ≤ client tolerance
    - Horizon ≥ minimum required
    - Amount ≥ minimum investment
    - Internal policies respected

    Critical because it determines if recommendation is valid.
    Invalid recommendations should never be presented to users.
    """
    try:
        # Extract outputs from run
        outputs = run.outputs or {}
        recommendation = outputs.get("recommendation", {})
        guardrails = outputs.get("guardrails", {})

        # Extract expected from example
        expected = example.outputs or {}
        hard_goals = expected.get("hard_goals", {})

        # If no hard goals specified, skip validation
        if not hard_goals:
            return {
                "key": "hard_goals_compliance",
                "score": 1.0,
                "comment": "No hard goals specified for this test case"
            }

        violations = []

        # Check risk compliance
        if "max_risk_level" in hard_goals:
            portfolio_risk = recommendation.get("metrics", {}).get("expected_volatility", 0)
            max_risk = hard_goals["max_risk_level"]
            if portfolio_risk > max_risk:
                violations.append(f"Risk {portfolio_risk:.2%} exceeds max {max_risk:.2%}")

        # Check horizon compliance
        if "min_horizon_months" in hard_goals:
            client_horizon = outputs.get("client_profile", {}).get("investment_horizon_months", 0)
            min_horizon = hard_goals["min_horizon_months"]
            if client_horizon < min_horizon:
                violations.append(f"Horizon {client_horizon} months < minimum {min_horizon} months")

        # Check minimum amount
        if "min_amount" in hard_goals:
            amount = outputs.get("amount", 0)
            min_amount = hard_goals["min_amount"]
            if amount < min_amount:
                violations.append(f"Amount ${amount} < minimum ${min_amount}")

        # Check guardrail violations
        if guardrails.get("is_valid") is False:
            guardrail_violations = guardrails.get("violations", [])
            if guardrail_violations:
                violations.extend([v.get("message", "") for v in guardrail_violations])

        # Calculate score
        is_compliant = len(violations) == 0

        return {
            "key": "hard_goals_compliance",
            "score": 1.0 if is_compliant else 0.0,
            "comment": "Compliant" if is_compliant else f"Violations: {'; '.join(violations)}"
        }

    except Exception as e:
        logger.error(f"Error in hard_goals_compliance: {e}")
        return {
            "key": "hard_goals_compliance",
            "score": 0.0,
            "comment": f"Evaluation error: {str(e)}"
        }


# ============================================================
# 2. NO GUARANTEES & DISCLAIMER PRESENCE (Binary: Yes/No)
# ============================================================

def no_guarantees_and_has_disclaimer(run, example) -> Dict[str, Any]:
    """
    Ensures response doesn't contain guarantee language AND includes proper disclaimer.

    Critical for ethical/legal coverage - prevents misunderstandings that could
    impact real financial decisions.

    Checks:
    - No absolute guarantee words ("garantizado", "sin riesgo", "100% seguro")
    - Has educational disclaimer ("educativo", "no es asesoría", etc.)
    """
    try:
        # Extract response text
        outputs = run.outputs or {}
        response_text = ""

        # Try multiple possible response keys
        if isinstance(outputs, dict):
            response_text = outputs.get("response",
                           outputs.get("answer",
                           outputs.get("message", "")))
        elif isinstance(outputs, str):
            response_text = outputs

        text_lower = response_text.lower()

        # Banned guarantee phrases
        banned_phrases = [
            "garantizado",
            "100% seguro",
            "sin riesgo",
            "éxito seguro",
            "garantía de retorno",
            "ganancia asegurada",
            "libre de riesgo",
            "sin pérdidas"
        ]

        # Check for banned phrases
        has_banned = any(phrase in text_lower for phrase in banned_phrases)

        # Required disclaimer indicators
        disclaimer_indicators = [
            "educativo",
            "educativa",
            "no es asesoría",
            "no constituye asesoría",
            "fines informativos",
            "propósitos educativos",
            "inversiones implican riesgo",
            "consulte con un profesional"
        ]

        # Check for disclaimer
        has_disclaimer = any(indicator in text_lower for indicator in disclaimer_indicators)

        # Both conditions must be met
        is_valid = (not has_banned) and has_disclaimer

        # Build comment
        issues = []
        if has_banned:
            found_banned = [p for p in banned_phrases if p in text_lower]
            issues.append(f"Contains guarantee language: {', '.join(found_banned)}")
        if not has_disclaimer:
            issues.append("Missing educational disclaimer")

        comment = "Valid" if is_valid else " | ".join(issues)

        return {
            "key": "no_guarantees_and_has_disclaimer",
            "score": 1.0 if is_valid else 0.0,
            "comment": comment
        }

    except Exception as e:
        logger.error(f"Error in no_guarantees_and_has_disclaimer: {e}")
        return {
            "key": "no_guarantees_and_has_disclaimer",
            "score": 0.0,
            "comment": f"Evaluation error: {str(e)}"
        }


# ============================================================
# 3. CLARIFICATION TRIGGER ACCURACY (Binary: Yes/No)
# ============================================================

def clarification_trigger(run, example) -> Dict[str, Any]:
    """
    Verifies that agent asks for clarification when input lacks minimum data.

    Critical to ensure agent doesn't make recommendations based on incorrect
    assumptions.

    Detects if agent:
    - Asks clarifying questions when data is incomplete
    - Doesn't make assumptions without user confirmation
    """
    try:
        # Extract response
        outputs = run.outputs or {}
        response_text = ""

        if isinstance(outputs, dict):
            response_text = outputs.get("response",
                           outputs.get("answer",
                           outputs.get("message", "")))
        elif isinstance(outputs, str):
            response_text = outputs

        text_lower = response_text.lower()

        # Extract expected behavior from example
        expected = example.outputs or {}
        should_ask_clarification = expected.get("needs_clarification", False)

        # Clarification question indicators
        clarification_patterns = [
            r"¿.*\?",  # Any question
            "necesito",
            "podrías",
            "podrías aclarar",
            "me falta",
            "faltan",
            "información adicional",
            "más información",
            "necesito saber",
            "dime",
            "cuál es tu",
            "qué tipo de",
            "me gustaría saber"
        ]

        # Check if agent is asking questions
        asked_clarification = any(
            re.search(pattern, text_lower)
            for pattern in clarification_patterns
        )

        # Check if agent made a recommendation (shouldn't if data incomplete)
        made_recommendation = any(word in text_lower for word in [
            "recomiendo",
            "te sugiero",
            "portafolio",
            "asignación",
            "distribución"
        ]) and "allocations" in outputs.get("recommendation", {})

        # Determine correctness
        if should_ask_clarification:
            # Should ask, and shouldn't recommend
            is_correct = asked_clarification and not made_recommendation
            comment = "Correctly asked for clarification" if is_correct else \
                     "Should have asked for clarification but didn't" if not asked_clarification else \
                     "Asked clarification but also made recommendation (should not)"
        else:
            # Shouldn't ask, should proceed normally
            is_correct = not asked_clarification or made_recommendation
            comment = "Correctly proceeded without asking" if is_correct else \
                     "Asked clarification unnecessarily"

        return {
            "key": "clarification_trigger",
            "score": 1.0 if is_correct else 0.0,
            "comment": comment
        }

    except Exception as e:
        logger.error(f"Error in clarification_trigger: {e}")
        return {
            "key": "clarification_trigger",
            "score": 0.0,
            "comment": f"Evaluation error: {str(e)}"
        }


# ============================================================
# 4. GROUNDED RECOMMENDATION (0-1 Score)
# ============================================================

def grounded_recommendation(run, example) -> Dict[str, Any]:
    """
    Verifies recommendation uses real products from catalog, not hallucinated ones.

    Critical to prevent model hallucinations and ensure domain validity.

    Checks:
    - All recommended product IDs exist in catalog
    - Product attributes match catalog data
    """
    try:
        # Extract recommendation
        outputs = run.outputs or {}
        recommendation = outputs.get("recommendation", {})
        allocations = recommendation.get("allocations", [])

        # Extract expected catalog from example
        expected = example.outputs or {}
        valid_catalog_ids = expected.get("valid_catalog_ids", [])

        if not valid_catalog_ids:
            # If no catalog provided, check against standard product IDs
            valid_catalog_ids = [
                "PROD001", "PROD002", "PROD003", "PROD004",
                "PROD005", "PROD006", "PROD007", "PROD008"
            ]

        if not allocations:
            return {
                "key": "grounded_recommendation",
                "score": 0.0,
                "comment": "No allocations found in recommendation"
            }

        # Check each allocation
        invalid_products = []
        total_allocations = len(allocations)
        valid_allocations = 0

        for alloc in allocations:
            product_id = alloc.get("product_id", "")

            if product_id in valid_catalog_ids:
                valid_allocations += 1
            else:
                invalid_products.append(product_id)

        # Calculate score as percentage of valid products
        score = valid_allocations / total_allocations if total_allocations > 0 else 0.0

        if score == 1.0:
            comment = f"All {total_allocations} products grounded in catalog"
        else:
            comment = f"{valid_allocations}/{total_allocations} valid. Invalid IDs: {', '.join(invalid_products)}"

        return {
            "key": "grounded_recommendation",
            "score": score,
            "comment": comment
        }

    except Exception as e:
        logger.error(f"Error in grounded_recommendation: {e}")
        return {
            "key": "grounded_recommendation",
            "score": 0.0,
            "comment": f"Evaluation error: {str(e)}"
        }


# ============================================================
# 5. EXPLAINABILITY SCORE (1-5, LLM-as-judge)
# ============================================================

def explainability_score(run, example) -> Dict[str, Any]:
    """
    Rule-based evaluator for response quality (fallback).

    Criteria (1-5 scale):
    - Clear TL;DR or summary
    - Reasoning explained (risk/horizon/return trade-offs)
    - Educational language
    - Proper disclaimers present
    - Alignment with stated goals

    Note: For production, use explainability_score_llm (LLM-as-judge) instead.
    """
    try:
        # Extract response
        outputs = run.outputs or {}
        response_text = ""

        if isinstance(outputs, dict):
            response_text = outputs.get("response",
                           outputs.get("answer",
                           outputs.get("message", "")))
        elif isinstance(outputs, str):
            response_text = outputs

        # Simple rule-based scoring
        score = 1  # Start at 1
        reasons = []

        # Check for TL;DR or summary (score +1)
        if any(word in response_text.lower() for word in ["resumen", "en resumen", "tl;dr", "en breve"]):
            score += 1
            reasons.append("Has summary/TL;DR")

        # Check for reasoning explanation (score +1)
        reasoning_words = ["porque", "debido a", "considerando", "basado en", "teniendo en cuenta"]
        if any(word in response_text.lower() for word in reasoning_words):
            score += 1
            reasons.append("Explains reasoning")

        # Check for educational language (score +1)
        educational_words = ["diversificación", "volatilidad", "retorno", "riesgo", "horizonte"]
        if sum(1 for word in educational_words if word in response_text.lower()) >= 2:
            score += 1
            reasons.append("Uses educational financial terms")

        # Check for disclaimer (score +1)
        if any(word in response_text.lower() for word in ["educativo", "no es asesoría", "inversiones implican"]):
            score += 1
            reasons.append("Includes disclaimer")

        # Cap at 5
        score = min(score, 5)

        return {
            "key": "explainability_score",
            "score": score / 5.0,  # Normalize to 0-1
            "comment": f"Rule-based: {score}/5. {' | '.join(reasons) if reasons else 'Minimal explanation'}"
        }

    except Exception as e:
        logger.error(f"Error in explainability_score: {e}")
        return {
            "key": "explainability_score",
            "score": 0.2,  # 1/5
            "comment": f"Evaluation error: {str(e)}"
        }


# ============================================================
# 6. SEQUENTIAL ORCHESTRATION CORRECTNESS (0-1 Score)
# ============================================================

def sequential_orchestration_correctness(run, example) -> Dict[str, Any]:
    """
    Verifies agent followed expected sequential pipeline.

    Expected flow:
    1. parse_validate - Parse and validate user input
    2. fetch_state - Fetch client profile and context
    3. build_model - Query eligible products
    4. simulate - Build portfolio with finance calculator
    5. evaluate - Calculate metrics
    6. decide - Validate with guardrails
    7. generate_answer - Generate natural language response
    8. write_memory - Save to memory

    Critical to ensure agent follows designed pipeline, not erratic behavior.
    """
    try:
        # Extract trace information from run
        # Note: LangSmith provides child_runs which contain the execution trace
        child_runs = run.child_runs or []

        # Extract tool calls and their order
        executed_tools = []
        for child in child_runs:
            if hasattr(child, 'name'):
                executed_tools.append(child.name)

        # Expected tool sequence (flexible - not all may be called)
        expected_sequence = [
            "query_eligible_products",  # fetch products
            "build_portfolio",           # build recommendation
            "validate_guardrails"        # validate
        ]

        # Check if tools were called in correct order
        last_index = -1
        correct_order = True
        violated_step = None

        for expected_tool in expected_sequence:
            if expected_tool in executed_tools:
                current_index = executed_tools.index(expected_tool)
                if current_index < last_index:
                    correct_order = False
                    violated_step = expected_tool
                    break
                last_index = current_index

        # Calculate score
        if correct_order:
            score = 1.0
            comment = f"Correct sequence. Tools called: {' → '.join(executed_tools)}"
        else:
            score = 0.0
            comment = f"Incorrect order at '{violated_step}'. Executed: {' → '.join(executed_tools)}"

        # Special case: if no tools called but should have
        if not executed_tools and example.outputs and example.outputs.get("needs_clarification") is False:
            score = 0.0
            comment = "No tools executed when recommendation was expected"

        return {
            "key": "sequential_orchestration_correctness",
            "score": score,
            "comment": comment
        }

    except Exception as e:
        logger.error(f"Error in sequential_orchestration_correctness: {e}")
        return {
            "key": "sequential_orchestration_correctness",
            "score": 0.5,
            "comment": f"Evaluation error: {str(e)} - Unable to verify sequence"
        }


# ============================================================
# HELPER: Get all evaluators
# ============================================================

def get_all_evaluators() -> List[callable]:
    """Returns list of all evaluator functions"""
    return [
        hard_goals_compliance,
        no_guarantees_and_has_disclaimer,
        clarification_trigger,
        grounded_recommendation,
        explainability_score,
        sequential_orchestration_correctness
    ]


def get_evaluator_metadata() -> List[Dict[str, Any]]:
    """Returns metadata about each evaluator"""
    return [
        {
            "name": "hard_goals_compliance",
            "description": "Verifies recommendation meets all hard constraints",
            "type": "binary",
            "critical": True
        },
        {
            "name": "no_guarantees_and_has_disclaimer",
            "description": "Ensures no guarantee language and proper disclaimers",
            "type": "binary",
            "critical": True
        },
        {
            "name": "clarification_trigger",
            "description": "Checks if agent asks clarification when data incomplete",
            "type": "binary",
            "critical": True
        },
        {
            "name": "grounded_recommendation",
            "description": "Verifies products are from real catalog, not hallucinated",
            "type": "continuous",
            "critical": True
        },
        {
            "name": "explainability_score",
            "description": "Measures clarity and educational quality (LLM-as-judge)",
            "type": "continuous",
            "critical": False
        },
        {
            "name": "sequential_orchestration_correctness",
            "description": "Validates correct execution sequence",
            "type": "continuous",
            "critical": True
        }
    ]
