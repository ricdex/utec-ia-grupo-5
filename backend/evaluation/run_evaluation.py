#!/usr/bin/env python3
"""
LangSmith Evaluation Runner for FinAdvisor

This script:
1. Creates/loads a dataset in LangSmith
2. Runs the FinAdvisor agent against test cases
3. Applies all 6 evaluators
4. Displays results

Usage:
    # Set your LangSmith API key in .env or export
    export LANGCHAIN_API_KEY="your-api-key"
    export LANGCHAIN_TRACING_V2="true"
    export LANGCHAIN_PROJECT="finadvisor-evaluation"

    # Run evaluation
    python backend/evaluation/run_evaluation.py

    # Run with specific dataset
    python backend/evaluation/run_evaluation.py --dataset-name "my-custom-dataset"
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

try:
    from langsmith import Client
    from langsmith.evaluation import evaluate
except ImportError:
    print("ERROR: langsmith not installed. Run: pip install langsmith")
    sys.exit(1)

from evaluation.evaluators import (
    hard_goals_compliance,
    no_guarantees_and_has_disclaimer,
    clarification_trigger,
    grounded_recommendation,
    explainability_score,
    sequential_orchestration_correctness
)

# Try to import LLM judge
try:
    from evaluation.llm_judge import get_llm_judge
    LLM_JUDGE_AVAILABLE = True
except ImportError:
    LLM_JUDGE_AVAILABLE = False
    print("Warning: LLM judge not available (langchain-anthropic not installed)")


def target_function(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Target function that runs the FinAdvisor agent.
    This is what LangSmith will evaluate.

    Args:
        inputs: Dict with 'client_id' and 'message'

    Returns:
        Dict with agent response and recommendation
    """
    from agent.fintech_agent import FinAdvisor

    client_id = inputs.get("client_id", "EVAL_CLIENT")
    message = inputs.get("message", "")

    # Create agent
    agent = FinAdvisor(client_id)

    # Get response
    response = agent.chat(message)

    # Try to extract recommendation if it was made
    recommendation = None
    guardrails = None

    # Check if memory has a recommendation
    memory_dict = agent.memory.to_dict()
    if "ltm" in memory_dict and "last_recommendation" in memory_dict["ltm"]:
        recommendation = memory_dict["ltm"]["last_recommendation"]

    return {
        "response": response,
        "recommendation": recommendation,
        "guardrails": guardrails,
        "client_profile": agent.memory.get_client_memory()
    }


def load_dataset_from_file(filepath: str) -> list:
    """Load dataset from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both formats
    if isinstance(data, dict) and "examples" in data:
        return data["examples"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError(f"Invalid dataset format in {filepath}")


def create_or_get_dataset(client: Client, dataset_name: str, examples: list) -> str:
    """Create dataset in LangSmith or get existing one"""

    # Check if dataset exists
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
        print(f"✓ Using existing dataset: {dataset_name}")
        return dataset.id
    except Exception:
        # Dataset doesn't exist, create it
        print(f"Creating new dataset: {dataset_name}")

        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="FinAdvisor evaluation dataset with test cases"
        )

        # Add examples
        for example in examples:
            client.create_example(
                dataset_id=dataset.id,
                inputs=example.get("inputs", {}),
                outputs=example.get("outputs", {})
            )

        print(f"✓ Created dataset with {len(examples)} examples")
        return dataset.id


def run_evaluation(
    dataset_name: str = "finadvisor-eval-dataset",
    dataset_file: str = None,
    experiment_prefix: str = "finadvisor-eval",
    use_llm_judge: bool = True
):
    """
    Run evaluation on FinAdvisor agent

    Args:
        dataset_name: Name of dataset in LangSmith
        dataset_file: Path to local JSON file with dataset (optional)
        experiment_prefix: Prefix for experiment name
        use_llm_judge: Use LLM-as-judge for explainability (default: True)
    """

    # Check API key
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("ERROR: LANGCHAIN_API_KEY not set")
        print("Get your key from: https://smith.langchain.com/settings")
        sys.exit(1)

    # Initialize LangSmith client
    client = Client()
    print(f"✓ Connected to LangSmith (Project: {os.getenv('LANGCHAIN_PROJECT', 'default')})")

    # Load dataset
    if dataset_file:
        examples = load_dataset_from_file(dataset_file)
        dataset_id = create_or_get_dataset(client, dataset_name, examples)
    else:
        # Use existing dataset
        try:
            dataset = client.read_dataset(dataset_name=dataset_name)
            dataset_id = dataset.id
            print(f"✓ Using existing dataset: {dataset_name}")
        except Exception as e:
            print(f"ERROR: Dataset '{dataset_name}' not found: {e}")
            print("Create it first or provide --dataset-file")
            sys.exit(1)

    # Define evaluators
    evaluators = [
        hard_goals_compliance,
        no_guarantees_and_has_disclaimer,
        clarification_trigger,
        grounded_recommendation,
        sequential_orchestration_correctness
    ]

    # Add explainability evaluator (LLM judge or rule-based)
    if use_llm_judge and LLM_JUDGE_AVAILABLE:
        llm_judge = get_llm_judge()
        if llm_judge:
            evaluators.append(llm_judge)
            print("✓ Using LLM-as-judge for explainability (Claude)")
        else:
            evaluators.append(explainability_score)
            print("⚠ LLM judge unavailable, using rule-based explainability")
    else:
        evaluators.append(explainability_score)
        print("ℹ Using rule-based explainability scoring")

    print(f"\n{'='*60}")
    print(f"Running evaluation with {len(evaluators)} evaluators:")
    for evaluator in evaluators:
        name = evaluator.__name__ if hasattr(evaluator, '__name__') else str(evaluator)
        print(f"  • {name}")
    print(f"{'='*60}\n")

    # Run evaluation
    results = evaluate(
        target_function,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        metadata={
            "version": "1.0.0",
            "agent": "FinAdvisor",
            "evaluator_count": len(evaluators)
        }
    )

    print(f"\n{'='*60}")
    print("Evaluation Complete!")
    print(f"{'='*60}")
    print(f"\nResults summary:")
    print(f"  View detailed results at: https://smith.langchain.com")
    print(f"  Project: {os.getenv('LANGCHAIN_PROJECT', 'default')}")
    print(f"  Experiment: {experiment_prefix}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run LangSmith evaluation on FinAdvisor agent"
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="finadvisor-eval-dataset",
        help="Name of dataset in LangSmith"
    )
    parser.add_argument(
        "--dataset-file",
        type=str,
        default="backend/evaluation/dataset.json",
        help="Path to JSON file with dataset (creates/updates dataset)"
    )
    parser.add_argument(
        "--experiment-prefix",
        type=str,
        default="finadvisor-eval",
        help="Prefix for experiment name"
    )
    parser.add_argument(
        "--use-llm-judge",
        action="store_true",
        default=True,
        help="Use LLM-as-judge for explainability (default: True)"
    )
    parser.add_argument(
        "--no-llm-judge",
        dest="use_llm_judge",
        action="store_false",
        help="Disable LLM-as-judge, use rule-based scoring"
    )

    args = parser.parse_args()

    # Check if running from project root
    if not os.path.exists("backend/evaluation/evaluators.py"):
        print("ERROR: Run this script from project root:")
        print("  python backend/evaluation/run_evaluation.py")
        sys.exit(1)

    # Run evaluation
    run_evaluation(
        dataset_name=args.dataset_name,
        dataset_file=args.dataset_file,
        experiment_prefix=args.experiment_prefix,
        use_llm_judge=args.use_llm_judge
    )


if __name__ == "__main__":
    main()
