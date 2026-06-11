"""
Experiment analysis and comparison tool.

Usage:
    python eval/analyze.py --runs experiments/runs/20260101_120000.json experiments/runs/20260101_121000.json
    python eval/analyze.py --runs_dir experiments/runs --latest 5
"""
import argparse
import json
import os
from typing import List, Dict, Any

from eval.metrics import compare_runs


def load_run(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "No data."
    headers = ["Run ID", "Strategy", "Model", "Accuracy", "Correct/Total", "Avg Steps", "Avg Out Tokens"]
    keys = ["run_id", "strategy", "model", "accuracy", "correct_total", "avg_reasoning_steps", "avg_output_tokens"]

    # Prepare formatted rows
    formatted = []
    for r in rows:
        formatted.append({
            "run_id": r.get("run_id", "")[-12:],
            "strategy": r.get("strategy", ""),
            "model": r.get("model", ""),
            "accuracy": f"{r.get('accuracy', 0.0):.4f}",
            "correct_total": f"{r.get('correct', 0)}/{r.get('total', 0)}",
            "avg_reasoning_steps": f"{r.get('avg_reasoning_steps', 0.0):.1f}",
            "avg_output_tokens": f"{r.get('avg_output_tokens', 0.0):.0f}",
        })

    # Compute column widths
    widths = {}
    for h, k in zip(headers, keys):
        max_len = max(len(h), max(len(str(row[k])) for row in formatted))
        widths[k] = max_len + 2

    # Build table
    lines = []
    header_line = "".join(h.ljust(widths[k]) for h, k in zip(headers, keys))
    lines.append(header_line)
    lines.append("-" * len(header_line))
    for row in formatted:
        lines.append("".join(str(row[k]).ljust(widths[k]) for k in keys))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze and compare COT experiment runs")
    parser.add_argument("--runs", nargs="+", help="Specific run JSON files to compare")
    parser.add_argument("--runs_dir", type=str, default="experiments/runs", help="Directory containing run files")
    parser.add_argument("--latest", type=int, default=None, help="Compare the N latest runs")
    args = parser.parse_args()

    if args.runs:
        paths = args.runs
    else:
        if not os.path.isdir(args.runs_dir):
            print(f"Directory not found: {args.runs_dir}")
            return
        files = [os.path.join(args.runs_dir, f) for f in os.listdir(args.runs_dir) if f.endswith(".json")]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        if args.latest:
            files = files[:args.latest]
        paths = files

    if not paths:
        print("No run files found.")
        return

    records = [load_run(p) for p in paths]
    comparison = compare_runs(records)

    print("=" * 80)
    print("Experiment Run Comparison")
    print("=" * 80)
    print(format_table(comparison["comparison"]))
    print("=" * 80)
    print(f"Best strategy: {comparison['best_strategy']} (accuracy: {comparison['best_accuracy']:.4f})")
    print("=" * 80)


if __name__ == "__main__":
    main()
