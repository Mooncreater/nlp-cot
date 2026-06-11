"""
Dry-run verification script for feat-004 (Base COT strategy).
Runs the full pipeline with a MockModel to verify correctness without API calls.
"""
import json
import os
import sys
from datetime import datetime

from eval.metrics import compute_metrics
from models.base import BaseModel
from strategies import BaseCOTStrategy
from tasks import AQuATask


class MockModel(BaseModel):
    """Mock LLM that returns canned responses for verification."""

    def __init__(self):
        super().__init__(model_name="mock-model")
        self.call_count = 0

    def generate(self, prompt, temperature=0.7, max_tokens=1024, stop=None, n=1, **kwargs):
        self.call_count += 1
        # Return a simple step-by-step + answer for any prompt
        return [
            "First, I need to understand what the question is asking.\n"
            "Then, I will set up the appropriate equations.\n"
            "After solving step by step, I find the correct value.\n"
            "Answer: A"
        ]

    def chat(self, messages, temperature=0.7, max_tokens=1024, stop=None, n=1, **kwargs):
        return self.generate("", temperature, max_tokens, stop, n, **kwargs)


def verify():
    print("=== feat-004 Verification (Base COT Dry-Run) ===\n")

    # 1. Load task and data
    task = AQuATask()
    examples = task.load_data(split="test")
    print(f"[1/6] Loaded {len(examples)} examples from AQuA test set")

    # Use only first 3 examples for quick verification
    examples = examples[:3]

    # 2. Verify prompt formatting
    sample_prompt = task.format_prompt(examples[0])
    assert "Question:" in sample_prompt
    assert "Options:" in sample_prompt
    print(f"[2/6] Prompt formatting OK\n  Sample prompt length: {len(sample_prompt)} chars")

    # 3. Verify answer extraction
    test_cases = [
        ("Some reasoning...\nAnswer: C", "C"),
        ("The answer is B.", "B"),
        ("Correct answer: D", "D"),
        ("I think A is right", "A"),
    ]
    for text, expected in test_cases:
        got = task.extract_answer(text)
        assert got == expected, f"Expected {expected}, got {got} for: {text}"
    print(f"[3/6] Answer extraction OK ({len(test_cases)} cases passed)")

    # 4. Run strategy with MockModel
    model = MockModel()
    strategy = BaseCOTStrategy(model=model, task=task)
    results = []
    for ex in examples:
        result = strategy.run(ex, temperature=0.7, max_tokens=512)
        results.append(result)
    print(f"[4/6] Strategy run OK ({model.call_count} mock API calls made)")

    # 5. Compute metrics
    metrics = compute_metrics(results, examples)
    assert "accuracy" in metrics
    assert "correct" in metrics
    assert "total" in metrics
    print(f"[5/6] Metrics computed OK")
    print(f"  Accuracy: {metrics['accuracy']:.4f} ({metrics['correct']}/{metrics['total']})")
    print(f"  Avg output tokens: {metrics['avg_output_tokens']:.1f}")

    # 6. Save results to experiments/runs/
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "experiments/runs"
    os.makedirs(output_dir, exist_ok=True)
    run_path = os.path.join(output_dir, f"verify_{run_id}.json")

    run_record = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "verification": True,
        "config": {
            "strategy": "base_cot",
            "task": "aqua",
            "model": "mock-model",
            "n_samples": len(examples),
        },
        "metrics": metrics,
        "results": [
            {
                "prediction": r["prediction"],
                "correct": ex.get("correct", ""),
                "output": r["output"],
            }
            for r, ex in zip(results, examples)
        ],
    }
    with open(run_path, "w", encoding="utf-8") as f:
        json.dump(run_record, f, ensure_ascii=False, indent=2)
    print(f"[6/6] Results saved to {run_path}")

    print("\n=== feat-004 Verification PASSED ===")
    print("The Base COT strategy pipeline is ready for real API experiments.")
    print("\nNext step: run a real experiment with")
    print("  python harness.py --strategy base_cot --dataset aqua --n_samples 100")
    return 0


if __name__ == "__main__":
    sys.exit(verify())
