"""
Dry-run verification for feat-010: BONUS — Harness Engineering Design Integration.

Verifies:
1. Every strategy declares harness_subsystems()
2. Coverage matrix is generated correctly
3. Subsystem evolution follows expected progression
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sys
sys.stdout.reconfigure(encoding='utf-8')

from models.base import BaseModel
from tasks.aqua_task import AQuATask
from strategies import (
    BaseCOTStrategy,
    SelfConsistencyStrategy,
    StepAwareVerifierStrategy,
    RAGCOTStrategy,
    MultiAgentDebateStrategy,
)
from retrieval import SimpleKeywordRetriever


class DummyModel(BaseModel):
    def __init__(self):
        super().__init__("dummy")

    def generate(self, prompt, **kwargs):
        return ["Answer: A"]

    def chat(self, messages, **kwargs):
        return ["Answer: A"]


def test_subsystem_declarations():
    model = DummyModel()
    task = AQuATask(data_dir="data/AQuA")
    retriever = SimpleKeywordRetriever(knowledge_path="data/knowledge_base.json")

    strategies = [
        ("base_cot", BaseCOTStrategy(model, task)),
        ("self_consistency", SelfConsistencyStrategy(model, task)),
        ("step_verifier", StepAwareVerifierStrategy(model, task)),
        ("rag_cot", RAGCOTStrategy(model, task, retriever)),
        ("multi_agent_debate", MultiAgentDebateStrategy(model, task)),
    ]

    expected = {
        "base_cot": {"instructions": True, "tools": False, "environment": True, "state": False, "feedback": False},
        "self_consistency": {"instructions": True, "tools": False, "environment": True, "state": True, "feedback": False},
        "step_verifier": {"instructions": True, "tools": True, "environment": True, "state": True, "feedback": True},
        "rag_cot": {"instructions": True, "tools": True, "environment": True, "state": True, "feedback": False},
        "multi_agent_debate": {"instructions": True, "tools": False, "environment": True, "state": True, "feedback": True},
    }

    for name, strat in strategies:
        sub = strat.harness_subsystems()
        assert set(sub.keys()) == {"instructions", "tools", "environment", "state", "feedback"}, \
            f"{name}: missing subsystem keys"
        assert sub == expected[name], f"{name}: subsystem mismatch. Got {sub}, expected {expected[name]}"
        info = strat.get_strategy_info()
        assert "harness_subsystems" in info, f"{name}: harness_subsystems not in get_strategy_info()"
    print("  subsystem declarations: PASS")


def test_progressive_activation():
    """Verify that advanced strategies activate more subsystems."""
    model = DummyModel()
    task = AQuATask(data_dir="data/AQuA")
    retriever = SimpleKeywordRetriever(knowledge_path="data/knowledge_base.json")

    base = BaseCOTStrategy(model, task).harness_subsystems()
    sc = SelfConsistencyStrategy(model, task).harness_subsystems()
    rag = RAGCOTStrategy(model, task, retriever).harness_subsystems()
    sv = StepAwareVerifierStrategy(model, task).harness_subsystems()
    mad = MultiAgentDebateStrategy(model, task).harness_subsystems()

    def count_active(sub):
        return sum(1 for v in sub.values() if v)

    assert count_active(base) <= count_active(sc), "self_consistency should have >= subsystems than base"
    assert count_active(sc) <= count_active(rag), "rag_cot should have >= subsystems than self_consistency"
    assert count_active(rag) <= count_active(sv), "step_verifier should have >= subsystems than rag_cot"
    assert count_active(sv) == 5, "step_verifier should be the only full 5-subsystem strategy"
    print("  progressive activation: PASS")


def test_harness_report():
    import subprocess
    result = subprocess.run(
        [sys.executable, "harness_report.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, f"harness_report.py failed: {result.stderr}"
    assert "Harness Engineering Subsystem Coverage Matrix" in result.stdout
    assert "base_cot" in result.stdout
    assert "step_verifier" in result.stdout
    assert "multi_agent_debate" in result.stdout
    print("  harness_report.py: PASS")


def main():
    print("=" * 60)
    print("feat-010 Dry-run Verification: Harness Engineering Integration")
    print("=" * 60)

    print("\n[Test 1] Subsystem declarations for all strategies...")
    test_subsystem_declarations()

    print("\n[Test 2] Progressive subsystem activation...")
    test_progressive_activation()

    print("\n[Test 3] harness_report.py execution...")
    test_harness_report()

    print("\n" + "=" * 60)
    print("PASS: All feat-010 checks passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
