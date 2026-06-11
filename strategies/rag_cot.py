"""
Retrieval-Augmented Chain-of-Thought (RAG+COT) strategy.
Based on: https://arxiv.org/abs/2212.09095 (IRCoT)

Before generating the reasoning chain, retrieve relevant knowledge
from an external knowledge base and inject it into the prompt.

Harness Engineering integration:
- Tools: the retriever is an external knowledge tool
- State: tracks retrieved context for each question
- Instructions: prompt explicitly instructs model to use retrieved knowledge
"""
import os
from typing import Dict, Any, List

from .base import BaseStrategy


class RAGCOTStrategy(BaseStrategy):
    """RAG-enhanced COT: retrieve then reason."""

    def harness_subsystems(self) -> Dict[str, bool]:
        return {
            "instructions": True,   # augmented prompt with retrieved context
            "tools": True,          # retriever as external knowledge tool
            "environment": True,
            "state": True,          # retrieved context tracked per question
            "feedback": False,
        }

    def __init__(
        self,
        model,
        task,
        retriever,
        prompt_template_path: str = "prompts/rag_cot.txt",
        base_prompt_path: str = "prompts/base_cot.txt",
        top_k: int = 3,
        **kwargs
    ):
        super().__init__(name="rag_cot", model=model, task=task, **kwargs)
        self.retriever = retriever
        self.top_k = top_k
        self.prompt_template_path = prompt_template_path
        self.base_prompt_path = base_prompt_path
        self.prompt_template = self._load_template(prompt_template_path)
        self.base_template = self._load_template(base_prompt_path)

    def _load_template(self, path: str) -> str:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _build_prompt(self, question: str, options_text: str, context: str) -> str:
        if self.prompt_template:
            return self.prompt_template.format(
                question=question,
                options=options_text,
                context=context,
            )
        # Fallback: inject context into base template
        base = self.base_template or (
            "You are solving a math word problem. Think step by step and explain your reasoning clearly.\n\n"
            "Question: {question}\n"
            "Options: {options}\n\n"
            "At the end of your response, you must state your final answer choice on a single line in exactly this format:\n"
            "Answer: X\n"
            "where X is one of A, B, C, D, or E."
        )
        context_block = (
            f"Relevant knowledge:\n{context}\n\n"
            "Use the above knowledge to help solve the problem. "
        ) if context else ""
        return context_block + base.format(question=question, options=options_text)

    def run(self, example: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        question = example.get("question", "")
        options = example.get("options", [])
        options_text = " ".join(options)

        # --- Phase 1: Retrieve relevant knowledge ---
        top_k = kwargs.get("top_k", self.top_k)
        print(f"    [RAG] Retrieving top-{top_k} docs...", end=" ")
        retrieved = self.retriever.retrieve(question, top_k=top_k)
        print(f"Found {len(retrieved)}")
        for i, doc in enumerate(retrieved, 1):
            print(f"      [{i}] score={doc.get('score', 0):.3f} | {doc.get('content', '')[:60]}...")

        if retrieved:
            context_lines = []
            for i, doc in enumerate(retrieved, 1):
                content = doc.get("content", "")
                context_lines.append(f"[{i}] {content}")
            context = "\n".join(context_lines)
        else:
            context = ""

        # --- Phase 2: Generate with augmented prompt ---
        prompt = self._build_prompt(question, options_text, context)

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
                "retrieved_context": retrieved,
                "num_docs": len(retrieved),
                "num_samples": len(outputs),
            },
        }
