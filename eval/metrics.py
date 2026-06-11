"""
Evaluation metrics for COT experiments.

Harness Engineering mapping:
- Feedback: computes quantitative feedback on strategy performance
"""
import re
from typing import List, Dict, Any


def compute_accuracy(predictions: List[str], examples: List[Dict[str, Any]]) -> float:
    """Compute accuracy over a list of predictions and examples."""
    if not predictions or not examples or len(predictions) != len(examples):
        return 0.0
    correct = sum(1 for pred, ex in zip(predictions, examples) if pred.upper() == ex.get("correct", "").upper())
    return correct / len(predictions)


def count_reasoning_steps(text: str) -> int:
    """
    Count approximate reasoning steps in a COT output.
    Strategy:
    1. Look for numbered steps (Step N:, N., (N))
    2. Fall back to paragraph count
    3. Exclude the final answer line
    """
    text = re.sub(r"(?i)answer\s*[:：]\s*[A-E]", "", text).strip()
    step_pattern = re.compile(
        r"(?:^|\n)\s*(?:Step\s*\d+[:.\)]?\s*|\d+[:.\)]\s+|\(\d+\)\s+)",
        re.IGNORECASE
    )
    parts = step_pattern.split(text)
    steps = [p.strip() for p in parts[1:] if len(p.strip()) > 10]
    if steps:
        return len(steps)
    # Fallback: count non-empty paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 15]
    return len(paragraphs) if paragraphs else 0


def compute_token_estimate(text: str) -> int:
    """Rough token estimate: ~0.75 tokens per word for English/Chinese mixed text."""
    words = len(text.split())
    return int(words / 0.75)


def compute_metrics(results: List[Dict[str, Any]], examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute full metrics for an experiment run.

    Args:
        results: List of result dicts from strategy.run()
        examples: List of original examples

    Returns:
        Dict with accuracy, reasoning steps, token estimates, etc.
    """
    predictions = [r.get("prediction", "") for r in results]
    correct_count = sum(
        1 for pred, ex in zip(predictions, examples) if pred.upper() == ex.get("correct", "").upper()
    )
    total = len(examples)
    accuracy = correct_count / total if total > 0 else 0.0

    # Per-example detailed metrics
    detailed = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_steps = 0

    for r, ex in zip(results, examples):
        output = r.get("output", "")
        pred = r.get("prediction", "")
        is_correct = pred.upper() == ex.get("correct", "").upper()
        steps = count_reasoning_steps(output)
        out_tokens = compute_token_estimate(output)
        # Input prompt tokens (rough estimate)
        prompt = r.get("metadata", {}).get("prompt", "")
        in_tokens = compute_token_estimate(prompt)

        total_output_tokens += out_tokens
        total_input_tokens += in_tokens
        total_steps += steps

        detailed.append({
            "prediction": pred,
            "correct": ex.get("correct", ""),
            "is_correct": is_correct,
            "reasoning_steps": steps,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
        })

    return {
        "accuracy": accuracy,
        "correct": correct_count,
        "total": total,
        "avg_reasoning_steps": total_steps / total if total > 0 else 0.0,
        "avg_input_tokens": total_input_tokens / total if total > 0 else 0.0,
        "avg_output_tokens": total_output_tokens / total if total > 0 else 0.0,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "detailed": detailed,
    }


def compare_runs(run_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare multiple experiment runs for controlled variable analysis.

    Args:
        run_records: List of run_record dicts loaded from experiments/runs/

    Returns:
        Comparison table and improvement stats.
    """
    comparison = []
    for record in run_records:
        config = record.get("config", {})
        metrics = record.get("metrics", {})
        comparison.append({
            "run_id": record.get("run_id", "unknown"),
            "strategy": config.get("strategy", "unknown"),
            "model": config.get("model", "unknown"),
            "accuracy": metrics.get("accuracy", 0.0),
            "correct": metrics.get("correct", 0),
            "total": metrics.get("total", 0),
            "avg_reasoning_steps": metrics.get("avg_reasoning_steps", 0.0),
            "avg_output_tokens": metrics.get("avg_output_tokens", 0.0),
        })

    # Sort by accuracy descending
    comparison.sort(key=lambda x: x["accuracy"], reverse=True)

    return {
        "comparison": comparison,
        "best_strategy": comparison[0]["strategy"] if comparison else None,
        "best_accuracy": comparison[0]["accuracy"] if comparison else 0.0,
    }
