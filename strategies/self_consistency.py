"""
Self-Consistency strategy.
Based on: https://arxiv.org/abs/2203.11171

Sample multiple reasoning paths for the same question,
then aggregate answers via majority voting.
"""
import os
from collections import Counter
from typing import Dict, Any, List

from .base import BaseStrategy


class SelfConsistencyStrategy(BaseStrategy):
    """Self-Consistency: multiple COT paths + majority voting."""

    def harness_subsystems(self) -> Dict[str, bool]:
        return {
            "instructions": True,
            "tools": False,
            "environment": True,
            "state": True,      # tracks multiple reasoning paths
            "feedback": False,  # voting is aggregation, not step-level feedback
        }

    def __init__(
        self,
        model,
        task,
        prompt_template_path: str = "prompts/base_cot.txt",
        n_paths: int = 5,
        temperature: float = 0.7,
        **kwargs
    ):
        super().__init__(name="self_consistency", model=model, task=task, **kwargs)
        self.n_paths = n_paths
        self.temperature = temperature
        self.prompt_template_path = prompt_template_path
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        if not os.path.exists(self.prompt_template_path):
            return (
                "You are solving a math word problem. Think step by step and explain your reasoning clearly.\n\n"
                "Question: {question}\n"
                "Options: {options}\n\n"
                "At the end of your response, you must state your final answer choice on a single line in exactly this format:\n"
                "Answer: X\n"
                "where X is one of A, B, C, D, or E."
            )
        with open(self.prompt_template_path, "r", encoding="utf-8") as f:
            return f.read()

    def run(self, example: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        question = example.get("question", "")
        options = example.get("options", [])
        options_text = " ".join(options)

        prompt = self.prompt_template.format(question=question, options=options_text)

        # Generate multiple reasoning paths
        n = kwargs.get("n_paths", self.n_paths)
        temp = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", 1024)

        # Generate multiple reasoning paths via sequential calls
        # (some API endpoints do not support n > 1 reliably)
        outputs = []
        for i in range(n):
            print(f"    [Self-Consistency] Generating path {i+1}/{n}...", end=" ")
            batch = self.model.generate(
                prompt,
                temperature=temp,
                max_tokens=max_tokens,
                n=1,
            )
            outputs.extend(batch)
            pred_preview = self.task.extract_answer(batch[0]) if batch else ""
            print(f"→ {pred_preview}")

        # Extract answer from each path
        predictions: List[str] = []
        for raw in outputs:
            pred = self.task.extract_answer(raw)
            predictions.append(pred)

        # Majority voting
        vote_counts = Counter(p for p in predictions if p)
        if not vote_counts:
            final_prediction = ""
        else:
            # Most common; ties broken by first appearance (Counter.most_common does this)
            final_prediction = vote_counts.most_common(1)[0][0]

        # Build a summary output for logging
        summary_lines = [
            f"=== Self-Consistency ({n} paths) ===",
            f"Votes: {dict(vote_counts)}",
            f"Final Answer: {final_prediction}",
            "",
            "--- Path 1 ---",
            outputs[0] if outputs else "",
        ]
        summary_output = "\n".join(summary_lines)

        return {
            "prediction": final_prediction,
            "output": summary_output,
            "metadata": {
                "prompt": prompt,
                "n_paths": n,
                "all_outputs": outputs,
                "all_predictions": predictions,
                "vote_counts": dict(vote_counts),
            },
        }
