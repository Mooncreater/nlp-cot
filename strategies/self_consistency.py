"""
Self-Consistency strategy.
Based on: https://arxiv.org/abs/2203.11171

Sample multiple reasoning paths for the same question, then aggregate answers.
This implementation improves plain majority voting with lightweight local
quality weighting, deterministic tie breaking, answer validation, retry for
empty predictions, and optional early stopping.
"""
import os
import re
from collections import Counter
from typing import Any, Dict, List, Tuple

from .base import BaseStrategy


class SelfConsistencyStrategy(BaseStrategy):
    """Self-Consistency: multiple COT paths + confidence-weighted voting."""

    MAX_PATH_WEIGHT = 2.5

    def harness_subsystems(self) -> Dict[str, bool]:
        return {
            "instructions": True,
            "tools": False,
            "environment": True,
            "state": True,      # tracks multiple reasoning paths and vote state
            "feedback": False,  # aggregation is not step-level feedback
        }

    def __init__(
        self,
        model,
        task,
        prompt_template_path: str = "prompts/base_cot.txt",
        n_paths: int = 5,
        temperature: float = 0.7,
        min_paths: int = 3,
        early_stop: bool = True,
        retry_on_empty: bool = True,
        **kwargs
    ):
        super().__init__(
            name="self_consistency",
            model=model,
            task=task,
            n_paths=n_paths,
            temperature=temperature,
            min_paths=min_paths,
            early_stop=early_stop,
            retry_on_empty=retry_on_empty,
            **kwargs
        )
        self.n_paths = n_paths
        self.temperature = temperature
        self.min_paths = max(1, min_paths)
        self.early_stop = early_stop
        self.retry_on_empty = retry_on_empty
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

    def _valid_choices(self, options: List[str]) -> set:
        """Infer allowed option labels from options, falling back to A-E."""
        labels = set()
        for option in options:
            match = re.match(r"\s*([A-E])[\).:]", str(option), re.IGNORECASE)
            if match:
                labels.add(match.group(1).upper())
        return labels or set("ABCDE")

    def _count_reasoning_steps(self, text: str) -> int:
        """Approximate how many explicit reasoning steps a path contains."""
        step_markers = re.findall(
            r"(?:^|\n)\s*(?:Step\s*\d+[:.\)]?|\d+[:.\)]\s+|\(\d+\)\s+)",
            text,
            flags=re.IGNORECASE,
        )
        if step_markers:
            return len(step_markers)

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 25]
        return len([p for p in paragraphs if not p.lower().startswith("answer")])

    def _path_quality(self, raw: str, prediction: str, valid_choices: set) -> Tuple[float, Dict[str, Any]]:
        """
        Score a sampled path before voting.

        The score is local and cheap: no extra API calls. It favors clear final
        answer formatting, concrete mathematical work, and non-trivial reasoning.
        """
        if not raw or prediction not in valid_choices:
            return 0.0, {
                "has_valid_prediction": False,
                "reasoning_steps": 0,
                "explicit_answer": False,
                "math_signal": 0,
                "penalties": ["missing_or_invalid_prediction"],
            }

        penalties: List[str] = []
        score = 1.0

        explicit_answer = bool(re.search(r"(?im)^\s*answer\s*:\s*[A-E]\s*$", raw))
        if explicit_answer:
            score += 0.35
        else:
            penalties.append("no_strict_answer_line")

        reasoning_steps = self._count_reasoning_steps(raw)
        score += min(reasoning_steps, 4) * 0.12

        math_signal = len(re.findall(r"\d+|[+\-*/=<>%$]", raw))
        score += min(math_signal, 10) * 0.03

        option_mentions = len(re.findall(r"\b[A-E]\)", raw))
        score += min(option_mentions, 2) * 0.05

        word_count = len(raw.split())
        if word_count < 25:
            score -= 0.25
            penalties.append("too_short")
        elif word_count > 260:
            score -= 0.15
            penalties.append("too_long")

        answer_mentions = re.findall(r"(?i)\banswer\s*[:is)]+\s*([A-E])", raw)
        distinct_answers = {answer.upper() for answer in answer_mentions}
        if len(distinct_answers) > 1:
            score -= 0.35
            penalties.append("conflicting_answer_mentions")

        score = max(0.1, min(score, self.MAX_PATH_WEIGHT))
        return score, {
            "has_valid_prediction": True,
            "reasoning_steps": reasoning_steps,
            "explicit_answer": explicit_answer,
            "math_signal": math_signal,
            "word_count": word_count,
            "penalties": penalties,
        }

    def _aggregate_votes(
        self,
        predictions: List[str],
        path_weights: List[float],
        valid_choices: set,
    ) -> Tuple[str, Dict[str, float], Dict[str, int]]:
        """Aggregate predictions with quality weights and deterministic tie breaking."""
        weighted_votes: Dict[str, float] = {label: 0.0 for label in sorted(valid_choices)}
        raw_counts: Counter = Counter()
        first_seen: Dict[str, int] = {}
        best_path_weight: Dict[str, float] = {}

        for idx, (pred, weight) in enumerate(zip(predictions, path_weights)):
            if pred not in valid_choices or weight <= 0:
                continue
            weighted_votes[pred] += weight
            raw_counts[pred] += 1
            first_seen.setdefault(pred, idx)
            best_path_weight[pred] = max(best_path_weight.get(pred, 0.0), weight)

        active_votes = {label: score for label, score in weighted_votes.items() if score > 0}
        if not active_votes:
            return "", {}, {}

        final_prediction = max(
            active_votes,
            key=lambda label: (
                active_votes[label],
                raw_counts[label],
                best_path_weight.get(label, 0.0),
                -first_seen[label],
            ),
        )
        return final_prediction, active_votes, dict(raw_counts)

    def _can_stop_early(
        self,
        predictions: List[str],
        path_weights: List[float],
        generated: int,
        target_n: int,
        min_paths: int,
    ) -> bool:
        """Stop when the weighted-vote leader cannot be overtaken by remaining paths."""
        if not self.early_stop or generated < min_paths:
            return False

        weighted_votes: Counter = Counter()
        for pred, weight in zip(predictions, path_weights):
            if pred and weight > 0:
                weighted_votes[pred] += weight
        if not weighted_votes:
            return False

        ranked = weighted_votes.most_common()
        leader_score = ranked[0][1]
        runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0
        remaining = target_n - generated
        return leader_score > runner_up_score + remaining * self.MAX_PATH_WEIGHT

    def run(self, example: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        question = example.get("question", "")
        options = example.get("options", [])
        options_text = " ".join(options)
        valid_choices = self._valid_choices(options)

        prompt = self.prompt_template.format(question=question, options=options_text)

        n = kwargs.get("n_paths", self.n_paths)
        temp = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", 1024)
        min_paths = min(max(1, kwargs.get("min_paths", self.min_paths)), n)
        retry_on_empty = kwargs.get("retry_on_empty", self.retry_on_empty)

        outputs: List[str] = []
        predictions: List[str] = []
        path_weights: List[float] = []
        path_quality_details: List[Dict[str, Any]] = []

        # Sequential calls are more compatible with DMXAPI-like endpoints than n > 1.
        for i in range(n):
            print(f"    [Self-Consistency] Generating path {i + 1}/{n}...", end=" ")
            batch = self.model.generate(
                prompt,
                temperature=temp,
                max_tokens=max_tokens,
                n=1,
            )
            raw = batch[0] if batch else ""
            pred = self.task.extract_answer(raw)

            if retry_on_empty and not pred:
                retry_batch = self.model.generate(
                    prompt,
                    temperature=max(0.2, temp * 0.5),
                    max_tokens=max_tokens,
                    n=1,
                )
                retry_raw = retry_batch[0] if retry_batch else ""
                retry_pred = self.task.extract_answer(retry_raw)
                if retry_pred:
                    raw, pred = retry_raw, retry_pred

            pred = pred if pred in valid_choices else ""
            weight, quality = self._path_quality(raw, pred, valid_choices)
            quality["path_index"] = i

            outputs.append(raw)
            predictions.append(pred)
            path_weights.append(weight)
            path_quality_details.append(quality)
            print(f"-> {pred or '?'} (weight={weight:.2f})")

            if self._can_stop_early(predictions, path_weights, len(outputs), n, min_paths):
                print(f"    [Self-Consistency] Early stop after {len(outputs)}/{n} paths.")
                break

        final_prediction, weighted_votes, vote_counts = self._aggregate_votes(
            predictions=predictions,
            path_weights=path_weights,
            valid_choices=valid_choices,
        )

        summary_lines = [
            f"=== Self-Consistency ({len(outputs)}/{n} paths) ===",
            f"Raw Votes: {vote_counts}",
            f"Weighted Votes: {weighted_votes}",
            f"Final Answer: {final_prediction}",
            "",
            "--- Path Summaries ---",
        ]
        for idx, (pred, weight, quality) in enumerate(zip(predictions, path_weights, path_quality_details)):
            summary_lines.append(
                f"Path {idx + 1}: pred={pred or '?'} weight={weight:.2f} "
                f"steps={quality.get('reasoning_steps', 0)} penalties={quality.get('penalties', [])}"
            )

        summary_lines.extend(["", "--- Selected Evidence Path ---"])
        if final_prediction:
            best_idx = max(
                range(len(outputs)),
                key=lambda idx: (
                    predictions[idx] == final_prediction,
                    path_weights[idx],
                    -idx,
                ),
            )
            summary_lines.append(outputs[best_idx])
        else:
            summary_lines.append(outputs[0] if outputs else "")
        summary_output = "\n".join(summary_lines)

        return {
            "prediction": final_prediction,
            "output": summary_output,
            "metadata": {
                "prompt": prompt,
                "n_paths": n,
                "generated_paths": len(outputs),
                "all_outputs": outputs,
                "all_predictions": predictions,
                "vote_counts": vote_counts,
                "weighted_votes": weighted_votes,
                "path_weights": path_weights,
                "path_quality_details": path_quality_details,
                "early_stopped": len(outputs) < n,
            },
        }
