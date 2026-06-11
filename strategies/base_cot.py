"""
Base Chain-of-Thought (COT) strategy.
Implements the classic "Let's think step by step" approach.
"""
import os
from typing import Dict, Any

from .base import BaseStrategy


class BaseCOTStrategy(BaseStrategy):
    """Basic COT reasoning with step-by-step prompting."""

    def harness_subsystems(self) -> Dict[str, bool]:
        return {
            "instructions": True,   # structured prompt template
            "tools": False,
            "environment": True,    # task-based answer extraction
            "state": False,         # no intermediate state tracking
            "feedback": False,      # no self-verification or critique
        }

    def __init__(self, model, task, prompt_template_path: str = "prompts/base_cot.txt", **kwargs):
        super().__init__(name="base_cot", model=model, task=task, **kwargs)
        self.prompt_template_path = prompt_template_path
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        if not os.path.exists(self.prompt_template_path):
            # Fallback default template
            return (
                "You are solving a math word problem. Think step by step and explain your reasoning clearly. "
                "After your reasoning, provide your final answer choice.\n\n"
                "Question: {question}\n"
                "Options: {options}\n\n"
                "Let's think step by step."
            )
        with open(self.prompt_template_path, "r", encoding="utf-8") as f:
            return f.read()

    def run(self, example: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        question = example.get("question", "")
        options = example.get("options", [])
        options_text = " ".join(options)

        prompt = self.prompt_template.format(question=question, options=options_text)

        outputs = self.model.generate(
            prompt,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 1024),
            n=kwargs.get("n", 1),
        )

        raw_output = outputs[0] if outputs else ""
        prediction = self.task.extract_answer(raw_output)

        return {
            "prediction": prediction,
            "output": raw_output,
            "metadata": {
                "prompt": prompt,
                "num_samples": len(outputs),
            },
        }
