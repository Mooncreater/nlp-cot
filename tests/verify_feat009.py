"""
Dry-run verification for feat-009: Evaluation metrics & experiment recording.
Tests metrics computation, run record structure, and analyze tool.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sys
sys.stdout.reconfigure(encoding='utf-8')

from eval.metrics import compute_metrics, compare_runs, count_reasoning_steps


def test_reasoning_steps():
    text1 = "Step 1: First do this.\nStep 2: Then do that.\nStep 3: Finally get result.\nAnswer: B"
    text2 = "Let me think.\n\nFirst, I calculate the value of x.\n\nThen, I add y to the result.\n\nAnswer: A"
    text3 = "Answer: C"
    assert count_reasoning_steps(text1) == 3, f"Expected 3, got {count_reasoning_steps(text1)}"
    assert count_reasoning_steps(text2) == 2, f"Expected 2, got {count_reasoning_steps(text2)}"
    assert count_reasoning_steps(text3) == 0, f"Expected 0, got {count_reasoning_steps(text3)}"
    print("  reasoning step counting: PASS")


def test_compute_metrics():
    examples = [
        {"correct": "B"},
        {"correct": "C"},
        {"correct": "B"},
    ]
    results = [
        {"prediction": "B", "output": "Step 1...\nStep 2...\nAnswer: B", "metadata": {"prompt": "Solve this"}},
        {"prediction": "C", "output": "Reasoning...\nAnswer: C", "metadata": {"prompt": "Solve that"}},
        {"prediction": "A", "output": "Wrong...\nAnswer: A", "metadata": {"prompt": "Solve other"}},
    ]
    metrics = compute_metrics(results, examples)
    assert metrics["accuracy"] == 2 / 3, f"Expected 0.6667, got {metrics['accuracy']}"
    assert metrics["correct"] == 2
    assert metrics["total"] == 3
    assert metrics["avg_reasoning_steps"] > 0
    assert metrics["avg_output_tokens"] > 0
    assert "detailed" in metrics
    assert len(metrics["detailed"]) == 3
    print("  compute_metrics: PASS")


def test_compare_runs():
    records = [
        {
            "run_id": "run_001",
            "config": {"strategy": "base_cot", "model": "dummy"},
            "metrics": {"accuracy": 0.6, "correct": 6, "total": 10, "avg_reasoning_steps": 3.0, "avg_output_tokens": 50.0},
        },
        {
            "run_id": "run_002",
            "config": {"strategy": "self_consistency", "model": "dummy"},
            "metrics": {"accuracy": 0.8, "correct": 8, "total": 10, "avg_reasoning_steps": 4.5, "avg_output_tokens": 120.0},
        },
    ]
    comp = compare_runs(records)
    assert comp["best_strategy"] == "self_consistency"
    assert comp["best_accuracy"] == 0.8
    assert len(comp["comparison"]) == 2
    print("  compare_runs: PASS")


def test_harness_registry():
    import subprocess
    result = subprocess.run([sys.executable, "harness.py", "--help"], capture_output=True, text=True)
    assert result.returncode == 0, f"harness.py --help failed: {result.stderr}"
    assert "--n_paths" in result.stdout
    assert "--n_agents" in result.stdout
    assert "--top_k" in result.stdout
    print("  harness.py registry & args: PASS")


def main():
    print("=" * 60)
    print("feat-009 Dry-run Verification: Metrics & Experiment Recording")
    print("=" * 60)

    print("\n[Test 1] Reasoning step counting...")
    test_reasoning_steps()

    print("\n[Test 2] compute_metrics with steps & tokens...")
    test_compute_metrics()

    print("\n[Test 3] compare_runs...")
    test_compare_runs()

    print("\n[Test 4] harness.py registry & argparse...")
    test_harness_registry()

    print("\n" + "=" * 60)
    print("PASS: All feat-009 checks passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
