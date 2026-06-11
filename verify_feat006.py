"""
Dry-run verification for feat-006: Step-Aware Verifier.
Uses a dummy model to test the verifier logic without real API calls.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from models.base import BaseModel
from tasks.aqua_task import AQuATask
from strategies.step_verifier import StepAwareVerifierStrategy


class DummyModel(BaseModel):
    """Dummy model that returns pre-defined reasoning paths for testing."""

    def __init__(self):
        super().__init__("dummy")
        self.call_count = 0

    def generate(self, prompt, temperature=0.7, max_tokens=1024, stop=None, n=1, **kwargs):
        self.call_count += 1
        # First call: generate reasoning paths
        if "Think step by step" in prompt or "Question:" in prompt:
            paths = [
                (
                    "Let's break this down.\n\n"
                    "Step 1: Identify the given information. The total cost is $50.\n"
                    "Step 2: Subtract the discount of $10.\n"
                    "Step 3: The final amount is $40.\n\n"
                    "Answer: B"
                ),
                (
                    "I need to find the final price.\n\n"
                    "Step 1: Start with $50.\n"
                    "Step 2: Apply 20% discount, which is $10.\n"
                    "Step 3: $50 - $10 = $40.\n\n"
                    "Answer: B"
                ),
                (
                    "Let me think.\n\n"
                    "Step 1: The original price is $50.\n"
                    "Step 2: Add tax of $5.\n"
                    "Step 3: Total is $55.\n\n"
                    "Answer: C"
                ),
            ]
            return paths[:n]
        # Subsequent calls: verifier scoring
        else:
            # Simulate verifier: steps mentioning "discount" or correct math get high scores
            # steps with "tax" or wrong direction get low scores
            step_text = ""
            for line in prompt.split("\n"):
                if line.startswith("Step to verify:"):
                    step_text = prompt.split("Step to verify:")[-1].strip()
                    break
            if not step_text:
                step_text = prompt

            if "discount" in step_text.lower() and "$10" in step_text:
                return ["Score: 9"]
            elif "$50 - $10 = $40" in step_text or "$40" in step_text:
                return ["Score: 10"]
            elif "tax" in step_text.lower():
                return ["Score: 2"]
            elif "$55" in step_text:
                return ["Score: 1"]
            elif "identify" in step_text.lower() or "given information" in step_text.lower():
                return ["Score: 7"]
            elif "start with" in step_text.lower():
                return ["Score: 8"]
            else:
                return ["Score: 5"]

    def chat(self, messages, temperature=0.7, max_tokens=1024, stop=None, n=1, **kwargs):
        prompt = messages[-1]["content"] if messages else ""
        return self.generate(prompt, temperature, max_tokens, stop, n, **kwargs)


def main():
    print("=" * 60)
    print("feat-006 Dry-run Verification: Step-Aware Verifier")
    print("=" * 60)

    model = DummyModel()
    task = AQuATask(data_dir="data/AQuA")
    strategy = StepAwareVerifierStrategy(
        model=model,
        task=task,
        n_paths=3,
        generator_temperature=0.7,
    )

    example = {
        "question": "A product costs $50. After a discount of $10, what is the final price?",
        "options": ["A) $60", "B) $40", "C) $55", "D) $45", "E) $50"],
        "correct": "B",
    }

    print(f"\n[Generator] Creating {strategy.n_paths} reasoning paths...")
    result = strategy.run(example)

    print("\n--- Result ---")
    print(f"Prediction: {result['prediction']}")
    print(f"Correct:    {example['correct']}")
    print(f"Match:      {result['prediction'].upper() == example['correct'].upper()}")

    meta = result["metadata"]
    print(f"\nPath scores: {meta['path_scores']}")
    print(f"Best path index: {meta['best_path_index']}")
    print(f"Best path avg score: {meta['best_path_avg_score']:.2f}")

    print("\n--- Step-level scores for best path ---")
    best_details = meta["path_step_details"][meta["best_path_index"]]
    for rec in best_details["steps"]:
        step_preview = rec["step"][:70] + "..." if len(rec["step"]) > 70 else rec["step"]
        print(f"  Score {rec['score']:.1f}: {step_preview}")

    print(f"\n--- Model API calls ---")
    print(f"Total calls: {model.call_count}")
    expected_calls = 1 + sum(len(s["steps"]) for s in meta["path_step_details"])
    print(f"Expected: 1 generation + {expected_calls - 1} verifications = {expected_calls}")

    print("\n" + "=" * 60)
    if result["prediction"].upper() == example["correct"].upper():
        print("PASS: Verifier correctly selected the path with valid reasoning.")
    else:
        print("FAIL: Verifier selected an incorrect path.")
    print("=" * 60)


if __name__ == "__main__":
    main()
