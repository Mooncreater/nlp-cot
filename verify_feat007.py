"""
Dry-run verification for feat-007: RAG + COT.
Tests retrieval-augmented reasoning with a dummy model.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from models.base import BaseModel
from tasks.aqua_task import AQuATask
from retrieval.simple_retriever import SimpleKeywordRetriever
from strategies.rag_cot import RAGCOTStrategy


class DummyModel(BaseModel):
    """Dummy model that checks whether retrieved context is present in the prompt."""

    def __init__(self):
        super().__init__("dummy")
        self.prompts_received = []

    def generate(self, prompt, temperature=0.7, max_tokens=1024, stop=None, n=1, **kwargs):
        self.prompts_received.append(prompt)
        # Return a response that echoes whether context was found
        has_context = "Relevant knowledge" in prompt or "Discount formula" in prompt
        if has_context:
            return [
                "Using the retrieved knowledge about discounts:\n"
                "Step 1: The original price is $50.\n"
                "Step 2: Apply the discount formula: Final price = $50 - $10 = $40.\n"
                "Answer: B"
            ]
        else:
            return [
                "I don't have relevant knowledge.\n"
                "Answer: B"
            ]

    def chat(self, messages, temperature=0.7, max_tokens=1024, stop=None, n=1, **kwargs):
        prompt = messages[-1]["content"] if messages else ""
        return self.generate(prompt, temperature, max_tokens, stop, n, **kwargs)


def main():
    print("=" * 60)
    print("feat-007 Dry-run Verification: RAG + COT")
    print("=" * 60)

    model = DummyModel()
    task = AQuATask(data_dir="data/AQuA")
    retriever = SimpleKeywordRetriever(knowledge_path="data/knowledge_base.json", top_k=2)
    strategy = RAGCOTStrategy(model=model, task=task, retriever=retriever, top_k=2)

    example = {
        "question": "A product costs $50. After a discount of $10, what is the final price?",
        "options": ["A) $60", "B) $40", "C) $55", "D) $45", "E) $50"],
        "correct": "B",
    }

    print(f"\n[Retriever] Top-{strategy.top_k} documents for question:")
    docs = retriever.retrieve(example["question"], top_k=2)
    for doc in docs:
        print(f"  score={doc['score']:.3f} | {doc['content'][:80]}...")

    result = strategy.run(example)

    print(f"\n--- Result ---")
    print(f"Prediction: {result['prediction']}")
    print(f"Correct:    {example['correct']}")
    print(f"Match:      {result['prediction'].upper() == example['correct'].upper()}")

    meta = result["metadata"]
    print(f"\nRetrieved docs: {meta['num_docs']}")
    print(f"Prompt contains context: {'Relevant knowledge' in model.prompts_received[-1]}")

    print("\n" + "=" * 60)
    if result["prediction"].upper() == example["correct"].upper():
        print("PASS: RAG+COT produced correct answer.")
    else:
        print("FAIL: RAG+COT produced incorrect answer.")
    print("=" * 60)


if __name__ == "__main__":
    main()
