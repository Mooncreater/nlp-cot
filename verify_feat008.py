"""
Dry-run verification for feat-008: Multi-Agent Debate.
Tests multi-agent reasoning and debate aggregation with a dummy model.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from models.base import BaseModel
from tasks.aqua_task import AQuATask
from strategies.multi_agent_debate import MultiAgentDebateStrategy


class DummyModel(BaseModel):
    """Dummy model that simulates agents with slight variations."""

    def __init__(self):
        super().__init__("dummy")
        self.call_count = 0

    def generate(self, prompt, temperature=0.7, max_tokens=1024, stop=None, n=1, **kwargs):
        self.call_count += 1
        # Simulate different agents based on round and role
        if "Agent 1" in prompt:
            if "Other agents" in prompt:
                return ["Agent 2 made a good point. I agree the answer is $40.\n\nAnswer: B"]
            return ["Step 1: Original price $50.\nStep 2: Discount $10.\nStep 3: $50 - $10 = $40.\n\nAnswer: B"]
        elif "Agent 2" in prompt:
            if "Other agents" in prompt:
                return ["I still believe the answer is $40 after considering all views.\n\nAnswer: B"]
            return ["Quick calculation: 50 - 10 = 40.\n\nAnswer: B"]
        elif "Agent 3" in prompt:
            if "Other agents" in prompt:
                return ["Hmm, I initially thought C but now I see B is correct.\n\nAnswer: B"]
            return ["Could there be tax? Let me check... Maybe $55?\n\nAnswer: C"]
        return ["Answer: B"]

    def chat(self, messages, temperature=0.7, max_tokens=1024, stop=None, n=1, **kwargs):
        prompt = messages[-1]["content"] if messages else ""
        return self.generate(prompt, temperature, max_tokens, stop, n, **kwargs)


def main():
    print("=" * 60)
    print("feat-008 Dry-run Verification: Multi-Agent Debate")
    print("=" * 60)

    model = DummyModel()
    task = AQuATask(data_dir="data/AQuA")
    strategy = MultiAgentDebateStrategy(model=model, task=task, n_agents=3, n_rounds=2)

    example = {
        "question": "A product costs $50. After a discount of $10, what is the final price?",
        "options": ["A) $60", "B) $40", "C) $55", "D) $45", "E) $50"],
        "correct": "B",
    }

    print(f"\n[Debate] Starting {strategy.n_agents} agents × {strategy.n_rounds} rounds...")
    result = strategy.run(example)

    print(f"\n--- Result ---")
    print(f"Prediction: {result['prediction']}")
    print(f"Correct:    {example['correct']}")
    print(f"Match:      {result['prediction'].upper() == example['correct'].upper()}")

    meta = result["metadata"]
    print(f"\nVote counts: {meta['vote_counts']}")
    print(f"Debate rounds: {meta['n_rounds']}")
    print(f"Agents: {meta['n_agents']}")

    print("\n--- Round-by-round predictions ---")
    for round_idx, round_data in enumerate(meta["debate_history"]):
        preds = [f"A{r['agent_id']+1}={r['prediction']}" for r in round_data]
        print(f"  Round {round_idx+1}: {', '.join(preds)}")

    print(f"\n--- Model API calls ---")
    print(f"Total calls: {model.call_count}")
    expected = strategy.n_agents * strategy.n_rounds
    print(f"Expected: {strategy.n_agents} agents × {strategy.n_rounds} rounds = {expected}")

    print("\n" + "=" * 60)
    if result["prediction"].upper() == example["correct"].upper():
        print("PASS: Multi-Agent Debate converged to correct answer.")
    else:
        print("FAIL: Debate did not converge to correct answer.")
    print("=" * 60)


if __name__ == "__main__":
    main()
